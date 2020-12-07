import os, re

from CIME.XML.compliances import Compliances

from visualCIME.visualCIME.ConfigVar import ConfigVar

class CompliancesHandler():
    def __init__(self, files):
        self.compliances = Compliances(files=files)

    def check_relation(self, relation, get_instance_value):
        relate_vars = self.compliances.get(relation,"vars").split('->')
        assert len(relate_vars)>=2, "The following relation has less than two xml variables (to be split by ->):"+relate_vars

        assertions = self.compliances.get_children("assert",root=relation)
        for assertion in assertions:
            rule = self.compliances.text(assertion)
            rule_vals = rule.split('->')
            assert len(relate_vars)==len(rule_vals), "Wrong number of arguments in assertion "+assertion

            print("relate_vars:", relate_vars)
            print("rule_vals:", rule_vals)
            rule_relevant = True
            for i in range(len(relate_vars)-1):
                instance_val = get_instance_value(relate_vars[i])
                if not re.search(rule_vals[i],instance_val):
                    rule_relevant = False
                    break
            if rule_relevant:
                errMsg = self.compliances.get(assertion,"errMsg")
                instance_val = get_instance_value(relate_vars[-1])
                if not re.search(rule_vals[-1],instance_val):
                    return False, errMsg

        '''
        rejections = self.get_children("reject",root=relation)
        for rejection in rejections:
            rule = self.text(rejection)
            rule_vals = rule.split('->')
            assert len(relate_vars)==len(rule_vals), "Wrong number of arguments in rejection "+rejection

            rule_relevant = True
            for i in range(len(relate_vars)-1):
                instance_val = get_xml_val(relate_vars[i],relation)
                if not re.search(rule_vals[i],instance_val):
                    rule_relevant = False
                    break
            if rule_relevant:
                errMsg = self.get(rejection,"errMsg")
                instance_val = get_xml_val(relate_vars[-1],relation)
                expect(not re.search(rule_vals[-1],instance_val),errMsg)
        '''
        return True,


    def check_compliances(self):   
        relations = self.compliances.get_children()
        for relation in relations:
            self.check_relation(relation, lambda cvName: ConfigVar.vdict[cvName].get_value())

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