import logging
import ipywidgets as widgets
from visualCIME.visualCIME.OutHandler import handler as owh

logger = logging.getLogger(__name__)

invalid_opt_icon = chr(int("1F534",base=16))        # red circle
valid_opt_icon = chr(int("1F534",base=16)+True)     # blue circle

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
        self.errMsgs = []
        ConfigVar.vdict[name] = self
        logger.debug("ConfigVar {} created.".format(self.name))

    @staticmethod
    def _opt_prefixed_with_status(option):
        """ Returns true if a given option str is prefixed with a status icon.

        Parameters
        ----------
        option: str
            A widget option/value.
        """
        return len(option)>0 and option.split()[0] in [invalid_opt_icon, valid_opt_icon]

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
    def observe_relations(self):
        for implication in self.compliances.implications(self.name):
            logger.debug("Observing relations for ConfigVar {}".format(self.name))
            if all([var in ConfigVar.vdict for var in implication.variables]):
                for var_other in set(implication.variables)-{self.name}:
                    ConfigVar.vdict[var_other].widget.observe(
                        self.update_states,
                        #names='value',
                        names='_property_lock',
                        type='change'
                    )
                    logger.debug("Added relational observance of {} for {}".format(var_other,self.name))

    @owh.out.capture()
    def _assign_states_select_widget(self, change=None, new_options=None):

        logger.debug("Assigning the states of options for ConfigVar {}".format(self.name))
        logger.debug("change: {}".format(change))
        if change != None:
            assert isinstance(change['owner'], widgets.Select) or isinstance(change['owner'], widgets.Dropdown)
            if not ConfigVar.value_is_valid(change['owner'].value):
                logger.debug("Invalid selection from owner. Do nothing for ConfigVar {}".format(self.name))
                return
            elif change['old'] == {}:
                logger.debug("Change in owner not finalized yet. Do nothing for ConfigVar {}".format(self.name))
                return

        self.unobserve_value_validity()

        old_value = self.widget.value
        if old_value != None:
            old_value_index = self.get_value_index()

        if new_options == None:
            new_options = self.widget.options
        new_options_w_states = []
        self.errMsgs = []
        for i in range(len(new_options)):
            option_stripped = ConfigVar.strip_option_status(new_options[i])

            logger.debug("Assigning the state of ConfigVar {} option: {}".format(self.name, option_stripped))
            def instance_val_getter(cvName):
                if cvName==self.name:
                    return option_stripped
                else:
                    val = ConfigVar.vdict[cvName].get_value()
                    if val == None:
                        val = "None"
                    return val

            status, errMsg = True, ''
            for implication in self.compliances.implications(self.name):
                try:
                    self.compliances.check_implication(
                        implication,
                        instance_val_getter
                        )
                except AssertionError as e:
                    errMsg = "{}".format(e)
                    status = False
                    break
            self.errMsgs.append(errMsg)
            if status == True:
                new_options_w_states.append('{}  {}'.format(valid_opt_icon, option_stripped))
            else:
                new_options_w_states.append('{}  {}'.format(invalid_opt_icon, option_stripped))
            logger.debug("ConfigVar {} option: {}, status: {}".format(self.name, option_stripped, status))

        new_options_w_states = tuple(new_options_w_states)
        if new_options_w_states != self.widget.options:
            logger.debug("State changes in the options of ConfigVar {}".format(self.name))
            self.widget.options = new_options_w_states
            self.widget.value = None # this is needed here to prevent a weird behavior:
                                     # in absence of this, widget selection clears for
                                     # some reason
            if old_value != None and len(self.widget.options) > old_value_index:
                self.widget.value = self.widget.options[old_value_index]
            elif len(self.widget.options)==1:
                option_split = self.widget.options[0].split()
                if len(option_split)>0 and option_split[0] == valid_opt_icon:
                    self.widget.value = self.widget.options[0]
            elif isinstance(self.widget, widgets.Dropdown):
                for option in self.widget.options:
                    option_split = option.split()
                    if len(option_split)>0 and option_split[0] == valid_opt_icon:
                        self.widget.value = option
                        break
        else:
            logger.debug("No state changes in the options of ConfigVar {}".format(self.name))

        self.observe_value_validity()

    @owh.out.capture()
    def update_states(self, change=None, new_options=None):
        logger.debug("Updating the states of options for ConfigVar {}".format(self.name))
        if isinstance(self.widget, widgets.Select) or isinstance(self.widget, widgets.Dropdown):
            self._assign_states_select_widget(change, new_options)
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
                logger.critical(self.errMsgs[new_index])
                from IPython.display import display, HTML, Javascript
                js = "<script>alert('ERROR: Invalid {} selection: {}');</script>".format(
                    self.name,
                    self.errMsgs[new_index]
                )
                display(HTML(js))
                self.widget.value = change['old']
            else:
                logger.debug("ConfigVar {} value is valid: {}".format(self.name, self.widget.value))
        else:
            raise NotImplementedError
