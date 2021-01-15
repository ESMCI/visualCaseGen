import os, re

from standard_script_setup import *

from visualCIME.visualCIME.ConfigVar import ConfigVar

class CompliancesHandler():

    def __init__(self, compliances):
        self.compliances = compliances
        ConfigVar.compliances = compliances

    def build_validity_observances(self):
        for var in ConfigVar.vdict:
            if len(self.compliances.implications(var))>0:
                ConfigVar.vdict[var].widget.observe(
                    ConfigVar.vdict[var].check_selection_validity,
                    names='_property_lock',
                    type='change')

    def build_relational_observances(self):
        for implication in self.compliances.implications():
            assert (len(implication.variables))>=2, "Compliance implications must involve at least two vars."

            if all([var in ConfigVar.vdict for var in implication.variables]):
                for var in implication.variables:
                    for var_other in set(implication.variables) - {var}:
                        ConfigVar.vdict[var_other].widget.observe(
                            ConfigVar.vdict[var].update_states,
                            #names='value'
                            names='_property_lock',
                            type='change'
                        )
