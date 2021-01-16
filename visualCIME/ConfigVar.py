import logging
from visualCIME.visualCIME.OutputVC import get_output_widget

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
            return self.widget.value[1:]
        else:
            return self.widget.value

    def get_value_index(self):
        try:
            return self.widget.options.index(self.widget.value)
        except:
            raise RuntimeError("ERROR: couldn't find value in options list")

    def assign_states(self, change=None):

        logger.debug("Assigning the states of options for ConfigVar {}".format(self.name))

        #if change and change['new'].split()[0] == chr(int("1F534",base=16)):
        #    return # invalid selection from source. do nothing. invalid selection will be rejected

        old_value_index = self.get_value_index()

        new_widget_options = []
        self.errMsgs = []
        for i in range(len(self.options)):
            option = self.options[i]
            logger.debug("ConfigVar {} option: {}".format(self.name, option))

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

        self.widget.options = new_widget_options
        self.widget.value = None # this is needed here to prevent a weird behavior:
                                 # in absence of this, widget selection clears for
                                 # some reason
        self.widget.value = self.widget.options[old_value_index]

    def update_states(self, change):
        with get_output_widget():
            logger.debug("Updating the states of options for ConfigVar {}".format(self.name))
            self.assign_states(change)

    def check_selection_validity(self, change):
        with get_output_widget():
            logger.debug("Checking option validity for ConfigVar {}".format(self.name))
            if 'index' in change['new']:
                new_index = change['new']['index']
                new_val = self.widget.options[new_index]
                if new_val.split()[0] == chr(int("1F534",base=16)):
                    logger.critical("Invalid selection for {}".format(self.name))
                    logger.critical(self.errMsgs[new_index])
                else:
                    get_output_widget().clear_output()

