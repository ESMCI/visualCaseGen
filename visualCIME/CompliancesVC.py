import os, re

from standard_script_setup import *
from CIME.XML.compliances import Compliances

class CompliancesVC(Compliances):
    """ A derived Compliances Class with added methods for Visual CIME (VC)"""

    def __init__(self, files):
        Compliances.__init__(self, files=files)

    def check_relation(self, relation, instance_val_getter):
        relate_vars = self.get(relation,"vars").split('~')
        assert len(relate_vars)>=2, "The following relation has less than two xml variables (to be split by ~):"+relate_vars

        assertions = self.get_children("assert",root=relation)
        for assertion in assertions:
            rule = self.text(assertion)
            rule_vals = rule.split('~')
            assert len(relate_vars)==len(rule_vals), "Wrong number of arguments in assertion "+assertion

            #print("relate_vars:", relate_vars)
            #print("rule_vals:", rule_vals)
            rule_relevant = True
            for i in range(len(relate_vars)-1):
                instance_val = instance_val_getter(relate_vars[i])
                if not re.search(rule_vals[i],instance_val):
                    rule_relevant = False
                    break
            if rule_relevant:
                errMsg = self.get(assertion,"errMsg")
                instance_val = instance_val_getter(relate_vars[-1])
                if not re.search(rule_vals[-1],instance_val):
                    return False, errMsg

        rejections = self.get_children("reject",root=relation)
        for rejection in rejections:
            rule = self.text(rejection)
            rule_vals = rule.split('~')
            assert len(relate_vars)==len(rule_vals), "Wrong number of arguments in rejection "+rejection

            rule_relevant = True
            for i in range(len(relate_vars)-1):
                instance_val = instance_val_getter(relate_vars[i])
                if not re.search(rule_vals[i],instance_val):
                    rule_relevant = False
                    break
            if rule_relevant:
                errMsg = self.get(rejection,"errMsg")
                instance_val = instance_val_getter(relate_vars[-1])
                if re.search(rule_vals[-1],instance_val):
                    return False, errMsg

        return True, ''
