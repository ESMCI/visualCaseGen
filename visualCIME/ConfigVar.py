from visualCIME.visualCIME.CompliancesVC import CompliancesVC
from visualCIME.visualCIME.OutputVC import get_output_widget

c_base = int("1F534",base=16)

class ConfigVar:

    # a collective dictionary of ConfigVars 
    vdict = dict()

    # to be set by CompliancesHandler constructor
    compliances = None

    def __init__(self, name):
        self.name = name
        self.options = set()
        self.widget = None
        self.relations = []
        ConfigVar.vdict[name] = self
        
    def get_value(self, strip_stat=False):
        assert self.widget != None, "Cannot determine value for "+self.name+". Associated widget not initialized."
        if strip_stat:
            return self.widget.value[1:] 
        else:
            return self.widget.value
    
    def assign_states(self):
        old_options = self.options
        states = [True for option in old_options]

        new_widget_options = []

        with get_output_widget():
            for option in self.options:

                def instance_val_getter(cvName):
                    if cvName==self.name:
                        return option
                    else:
                        return ConfigVar.vdict[cvName].get_value(strip_stat=True)

                status, errMsg = True, ''
                for relation in self.relations:
                    status, errMsg = ConfigVar.compliances.check_relation(relation, instance_val_getter)
                    if status==False:
                        break

                new_widget_options.append('{}  {}'.format(chr(c_base+status), option))
            self.widget.options = new_widget_options

    def update_states(self, change):
        self.assign_states()