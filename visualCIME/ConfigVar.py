import logging
import ipywidgets as widgets
from visualCIME.visualCIME.OutHandler import handler as owh

logger = logging.getLogger(__name__)

c_base_red = int("1F534",base=16)

class ConfigVar:

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
    def value_is_valid(val):
        if val == None:
            return True
        val_split = val.split()
        if len(val_split)>=2:
            if val_split[0] == chr(c_base_red):
                return False
            elif val_split[0] == chr(c_base_red+True):
                return True
        else:
            raise RuntimeError("Corrupt value passed to value_is_valid(): {}".format(val))

    @staticmethod
    def strip_option_status(option):
        if option.split()[0] in [chr(c_base_red), chr(c_base_red+True)]:
            return option[1:].strip()
        else:
            return option

    def get_value(self):
        assert self.widget != None, "Cannot determine value for "+self.name+". Associated widget not initialized."
        if self.widget.value!=None and self.widget.value.split()[0] in [chr(c_base_red), chr(c_base_red+True)]:
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
    def _assign_states_select_widget(self, change=None):

        logger.debug("Assigning the states of options for ConfigVar {}".format(self.name))
        logger.debug("change: {}".format(change))
        if change != None:
            assert isinstance(change['owner'], widgets.Select)
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

        new_widget_options = []
        self.errMsgs = []
        for i in range(len(self.widget.options)):
            option_stripped = ConfigVar.strip_option_status(self.widget.options[i])

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
            new_widget_options.append('{}  {}'.format(chr(c_base_red+status), option_stripped))
            logger.debug("ConfigVar {} option: {}, status: {}".format(self.name, option_stripped, status))

        self.widget.options = new_widget_options
        self.widget.value = None # this is needed here to prevent a weird behavior:
                                 # in absence of this, widget selection clears for
                                 # some reason
        if old_value != None:
            self.widget.value = self.widget.options[old_value_index]

        self.observe_value_validity()

    @owh.out.capture()
    def update_states(self, change=None):
        logger.debug("Updating the states of options for ConfigVar {}".format(self.name))
        if isinstance(self.widget, widgets.Select):
            self._assign_states_select_widget(change)
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

                #todo: improve below block that handles COMP_MODE and COMP_OPTION widget options
                if self.name.startswith('COMP') and len(self.name)==8:
                    comp_class = self.name[5:8]
                    model = ConfigVar.strip_option_status(self.widget.value)
                    from CIME.XML.files import Files
                    from visualCIME.visualCIME.CIME_interface import get_comp_desc
                    files = Files(comp_interface="nuopc")
                    comp_modes, comp_options = get_comp_desc(comp_class, model, files)
                    if comp_class and model and len(comp_class)>0 and len(model)>0:
                        ConfigVar.vdict["COMP_{}_MODE".format(comp_class)].widget.options = [chr(c_base_red+True)+' {}'.format(mode) for mode in comp_modes]
                        ConfigVar.vdict["COMP_{}_MODE".format(comp_class)].update_states()
                        ConfigVar.vdict["COMP_{}_OPTION".format(comp_class)].widget.options = comp_options
                        ConfigVar.vdict["COMP_{}_OPTION".format(comp_class)].update_states()
        else:
            raise NotImplementedError

                #new_index = change['new']['index']
                #new_val = self.widget.options[new_index]
                #logger.debug("New option val: {}".format(new_val))
                #if new_val.split()[0] == chr(int("1F534",base=16)):
                    #logger.critical("ERROR: Invalid selection for {}".format(self.name))
                    #logger.critical(self.errMsgs[new_index])
                    #selection_valid = False
                #else:
                    #get_output_widget().clear_output()
        #if not selection_valid:
            #old_index = self.get_value_index()
            #with get_output_widget():
                #logger.debug("setting ConfigVar {} value to {}".format(self.name, self.widget.options[old_index]))
            #self.widget.value = None
            #self.widget.value = self.widget.options[old_index]
            #with get_output_widget():
                #print("dbg:", self.widget.value)


