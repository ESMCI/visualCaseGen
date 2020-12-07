from visualCIME.visualCIME.CompliancesVC import CompliancesVC

c_base = int("1F534",base=16)

class ConfigVar:

    # a collective dictionary of ConfigVars 
    vdict = dict()

    def __init__(self, name):
        self.name = name
        self.options = set()
        self.widget = None
        self.relations = []
        ConfigVar.vdict[name] = self
        
    def get_value(self):
        assert self.widget != None, "Cannot determine value for "+self.name+". Associated widget not initialized."
        print(type(self.widget.value), self.widget.value)
        return self.widget.value
    
    def assign_states(self):
        old_options = self.options
        states = [True for option in old_options]
                    
        self.widget.options = ['{}  {}'.format(chr(c_base+s), o) for s,o in zip(states,old_options)]
    
    def update_states(self, change):
        self.assign_states()