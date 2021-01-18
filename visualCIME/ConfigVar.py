import logging
from visualCIME.visualCIME.OutputVC import get_output_widget
import ipywidgets as widgets

logger = logging.getLogger(__name__)

c_base = int("1F534",base=16)

class ConfigVar:

    # a collective dictionary of ConfigVars
    vdict = dict()

    # to be set by CompliancesHandler constructor
    compliances = None

    def __init__(self, name):
        if name in ConfigVar.vdict:
            logger.warning("ConfigVar {} already created.".format(name))
        self.name = name
        self.options = []
        self.widget = None
        self.errMsgs = []
        ConfigVar.vdict[name] = self
        logger.debug("ConfigVar {} created.".format(self.name))

    def get_value(self, strip_stat=False):
        assert self.widget != None, "Cannot determine value for "+self.name+". Associated widget not initialized."
        if strip_stat:
            return self.widget.value[1:].strip()
        else:
            return self.widget.value

    def get_value_index(self):
        try:
            return self.widget.options.index(self.widget.value)
        except:
            raise RuntimeError("ERROR: couldn't find value in options list")

    def _assign_states_select_widget(self, change=None):

        with get_output_widget():
            logger.debug("Assigning the states of options for ConfigVar {}".format(self.name))
            logger.debug("change: {}".format(change))
        if change != None:
            assert isinstance(change['owner'], widgets.Select)
            if change['owner'].value.split()[0] == chr(int("1F534",base=16)):
                with get_output_widget():
                    logger.debug("Invalid selection from owner. Do nothing for ConfigVar {}".format(self.name))
                return
            elif change['old'] == {}:
                with get_output_widget():
                    logger.debug("Change in owner not finalized yet. Do nothing for ConfigVar {}".format(self.name))
                return

        old_value_index = self.get_value_index()
        new_widget_options = []
        self.errMsgs = []

        with get_output_widget():
            for i in range(len(self.options)):
                option = self.options[i]

                logger.debug("Assigning the state of ConfigVar {} option: {}".format(self.name, option))
                def instance_val_getter(cvName):
                    if cvName==self.name:
                        return option
                    else:
                        return ConfigVar.vdict[cvName].get_value(strip_stat=True)

                status, errMsg = True, ''
                for implication in self.compliances.implications(self.name):
                    try:
                        self.compliances.check_implication(
                            implication,
                            instance_val_getter
                            )
                    except AssertionError as e:
                        errMsg = e
                        status = False
                        break
                self.errMsgs.append(errMsg)
                new_widget_options.append('{}  {}'.format(chr(c_base+status), option))
                logger.debug("ConfigVar {} option: {}, status: {}".format(self.name, option, status))

        self.widget.options = new_widget_options
        self.widget.value = None # this is needed here to prevent a weird behavior:
                                 # in absence of this, widget selection clears for
                                 # some reason
        self.widget.value = self.widget.options[old_value_index]

    def update_states(self, change=None):
        with get_output_widget():
            logger.debug("Updating the states of options for ConfigVar {}".format(self.name))
        if isinstance(self.widget, widgets.Select):
            self._assign_states_select_widget(change)
        else:
            raise NotImplementedError

    def check_selection_validity(self, change):
        with get_output_widget():
            logger.debug("Checking option validity for ConfigVar {}".format(self.name))
            if 'index' in change['new']:
                new_index = change['new']['index']
                new_val = self.widget.options[new_index]
                logger.debug("New option val: {}".format(new_val))
                if new_val.split()[0] == chr(int("1F534",base=16)):
                    logger.critical("ERROR: Invalid selection for {}".format(self.name))
                    logger.critical(self.errMsgs[new_index])
                else:
                    get_output_widget().clear_output()

