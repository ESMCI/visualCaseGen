import os, re

from standard_script_setup import *

from visualCIME.visualCIME.ConfigVar import ConfigVar
from visualCIME.visualCIME.CompliancesVC import CompliancesVC

class CompliancesHandler():

    def __init__(self, compliances):
        self.compliances = compliances
        ConfigVar.compliances = compliances

    def check_compliances(self):   
        relations = self.compliances.get_children()
        for relation in relations:
            status, errMsg = self.compliances.check_relation(relation, lambda cvName: ConfigVar.vdict[cvName].get_value(strip_stat=True))
            if status==False:
                print("Compliance violation:", errMsg)
                return

        print("done. no compliance violation.")


    def build_links(self):
        relations = self.compliances.get_children()
        for relation in relations:
            # relate_vars: xml case vars to be checked for relational integrity
            relate_vars = self.compliances.get(relation,"vars").split('->')
            assert len(relate_vars)>=2, "The following relation has less than two xml variables (to be split by ->):"+relate_vars
            
            # add relation to relation member of each relevant variable
            if all([relate_var in ConfigVar.vdict for relate_var in relate_vars]):
                for relate_var in relate_vars:
                    ConfigVar.vdict[relate_var].relations.append(relation)
            
            # last variable of the relation
            cv_affected = ConfigVar.vdict[relate_vars[-1]]
            
            # all other variables of the relation
            for i in range(len(relate_vars)-1):
                cv_influence = ConfigVar.vdict[relate_vars[i]]    
                cv_influence.widget.observe(cv_affected.update_states, names='value')