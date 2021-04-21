import logging
import ipywidgets as widgets
from visualCIME.visualCIME.OutHandler import handler as owh

logger = logging.getLogger(__name__)

invalid_opt_icon = chr(int("2718",base=16)) # Ballot Box with X
valid_opt_icon = chr(int("2713",base=16)) # Ballot Box with X

# it is assumed in this module that icons lenghts are one char.
assert len(invalid_opt_icon)==1 and len(valid_opt_icon)==1

class ConfigVar:

    """
    CESM Configuration variable, e.g., COMP_OCN xml variable.
    """

    # a collective dictionary of ConfigVars
    vdict = dict()

    # to be set by CompliancesHandler constructor
    compliances = None

    def __init__(self, name):
        if name in ConfigVar.vdict:
            logger.warning("ConfigVar {} already created.".format(name))
        self.name = name
        self.widget = None
        self.options_validity = []
        self.error_msgs = []
        ConfigVar.vdict[name] = self
        logger.debug("ConfigVar {} created.".format(self.name))

    def reset():
        logger.debug("Resetting ConfigVar vdict.")
        ConfigVar.vdict = dict()

    @staticmethod
    def _opt_prefixed_with_status(option):
        """ Returns true if a given option str is prefixed with a status icon.

        Parameters
        ----------
        option: str
            A widget option/value.

        Returns
        -------
        True or False
        """
        return len(option)>0 and option.split()[0] in [invalid_opt_icon, valid_opt_icon]

    @owh.out.capture()
    def options_sans_validity(self):
        return [option[1:].strip() if option.split()[0] in [invalid_opt_icon, valid_opt_icon] else option \
                for option in self.widget.options]

    @staticmethod
    def value_is_valid(val):
        if val == None:
            return True
        val_split = val.split()
        if len(val_split)>=2:
            if val_split[0] == invalid_opt_icon:
                return False
            elif val_split[0] == valid_opt_icon:
                return True
        else:
            raise RuntimeError("Corrupt value passed to value_is_valid(): {}".format(val))

    @staticmethod
    def strip_option_status(option):
        if ConfigVar._opt_prefixed_with_status(option):
            return option[1:].strip()
        else:
            return option

    def is_supported_widget(self):
        return isinstance(self.widget, widgets.ToggleButtons) or \
            isinstance(self.widget, widgets.Select) or \
            isinstance(self.widget, widgets.Dropdown)

    @owh.out.capture()
    def get_options_validity_icons(self):
        return [valid_opt_icon if valid else invalid_opt_icon for valid in self.options_validity]

    def get_value(self):
        assert self.widget != None, "Cannot determine value for "+self.name+". Associated widget not initialized."
        if self.widget.value!=None and ConfigVar._opt_prefixed_with_status(self.widget.value):
            return self.widget.value[1:].strip()
        else:
            return self.widget.value

    def get_value_index(self):
        if self.widget.value == None:
            return None
        try:
            return self.widget.options.index(self.widget.value)
        except:
            raise RuntimeError("ERROR: couldn't find value in options list")

    @owh.out.capture()
    def observe_value_validity(self):
        if len(self.compliances.implications(self.name))>0:
            logger.debug("Observing value validity for ConfigVar {}".format(self.name))
            self.widget.observe(
                self._check_selection_validity,
                names='value',
                type='change')

    @owh.out.capture()
    def unobserve_value_validity(self):
        if len(self.compliances.implications(self.name))>0:
            logger.debug("Unobserving value validity for ConfigVar {}".format(self.name))
            self.widget.unobserve(
                self._check_selection_validity,
                names='value',
                type='change')


    @owh.out.capture()
    def update_options_validity(self, change=None):
        """Re-evaluates the validity of widget options and updates option validity icons """

        logger.debug("Updating option validities of ConfigVar {}".format(self.name))

        # If this method is called due to a change in an observed widget,
        # check if the options of this ConfigVar need to be updated yet.
        if change != None:
            logger.debug("change: {}".format(change))
            if not ConfigVar.value_is_valid(change['owner'].value):
                logger.debug("Invalid selection at change owner. Do nothing for observing ConfigVar {}"\
                    .format(self.name))
                return
            elif change['old'] == {}:
                logger.debug("Change in owner not finalized yet. Do nothing for ConfigVar {}".format(self.name))
                return

        assert self.is_supported_widget(), "ConfigVar {} widget is not supported yet.".format(self.name)

        self.options_validity = [True]*len(self.widget.options)
        self.error_msgs = ['']*len(self.widget.options)

        options_sans_validity = self.options_sans_validity()

        for i in range(len(options_sans_validity)):
            option = options_sans_validity[i]
            assert option.split()[0] not in [valid_opt_icon, invalid_opt_icon]

            def _instance_val_getter(cvName):
                val = ConfigVar.vdict[cvName].get_value()
                if val == None:
                    val = "None"
                return val
            def _instance_val_getter_opt(cvName):
                if cvName == self.name:
                    return option
                val = ConfigVar.vdict[cvName].get_value()
                if val == None:
                    val = "None"
                return val


            status, errMsg = True, ''
            for implication in self.compliances.implications(self.name):
                try:
                    self.compliances.check_implication(
                        implication,
                        _instance_val_getter,
                        _instance_val_getter_opt,
                    )
                except AssertionError as e:
                    self.options_validity[i] = False
                    self.error_msgs[i] = "{}".format(e)
                    break

        options_validity_icons = self.get_options_validity_icons()
        new_widget_options = \
            ['{} {}'.format(options_validity_icons[i], options_sans_validity[i]) \
                for i in range(len(options_sans_validity))]

        if self.widget.options == new_widget_options:
            logger.debug("No validity changes in {}".format(self.name))
            return # no change in options validity
        else:
            logger.debug("Validity changes in the options of ConfigVar {}".format(self.name))

            old_val = self.widget.value
            if old_val:
               old_val_idx = self.get_value_index()

            self.unobserve_value_validity()
            self.widget.options = new_widget_options
            self.widget.value = None # this is needed here to prevent a weird behavior:
                         # in absence of this, widget selection clears for
                         # some reason

            if old_val != None and options_validity_icons[old_val_idx] != invalid_opt_icon:
                self.widget.value = self.widget.options[old_val_idx]
            self.observe_value_validity()
            logger.debug("Options validity updated for {}".format(self.name))

    @owh.out.capture()
    def update_options(self, new_options=None, tooltips=None, init_value=False):
        """Assigns the options displayed in the widget."""

        logger.debug("Updating the options of ConfigVar {}".format(self.name))

        # First, update to new options
        self.unobserve_value_validity()
        self.widget.options = new_options
        self.widget.value = None
        self.observe_value_validity()

        # Second, update options validities
        self.update_options_validity()

        # If requested, pick the first valid value:
        if init_value==True and self.widget.value==None:
            for option in self.widget.options:
                if ConfigVar.value_is_valid(option):
                    self.widget.value = option
                    break

        # Finally, update tooltips
        if tooltips:
            if isinstance(self.widget, widgets.ToggleButtons):
                self.widget.tooltips = tooltips
            else:
                raise NotImplementedError

    @owh.out.capture()
    def _check_selection_validity(self, change):

        logger.debug("Checking the validity for ConfigVar {} with value={}".format(self.name, self.widget.value))

        if change != None:
            assert change['name'] == 'value'
            new_val = change['new']
            if new_val != None and not ConfigVar.value_is_valid(new_val):
                new_index = self.get_value_index()
                logger.critical("ERROR: Invalid selection for {}".format(self.name))
                logger.critical(self.error_msgs[new_index])
                from IPython.display import display, HTML, Javascript
                js = "<script>alert('ERROR: Invalid {} selection: {}');</script>".format(
                    self.name,
                    self.error_msgs[new_index]
                )
                display(HTML(js))
                self.widget.value = change['old']
            else:
                logger.debug("ConfigVar {} value is valid: {}".format(self.name, self.widget.value))
        else:
            raise NotImplementedError
