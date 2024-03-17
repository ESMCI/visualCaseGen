"""Module to define and register ConfigVars"""

import logging
from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.config_var_str_ms import ConfigVarStrMS

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_custom_compset_variables(cime):

    # Custom Compset Variables

    ConfigVarStr("INITTIME")

    for comp_class in cime.comp_classes:
        ConfigVarStr(f"COMP_{comp_class}")
        ConfigVarStr(f"COMP_{comp_class}_PHYS")
        ConfigVarStrMS(f"COMP_{comp_class}_OPTION")

    # Auxiliary COMPSET_LNAME is set automatically every time:
    #   (1) COMPSET_ALIAS is (re-)assigned, or
    #   (2) Corresponding COMP_???_PHYS or COMP_???_OPTION variables are (re-)assigned 
    ConfigVarStr("COMPSET_LNAME")

    def update_compset_lname(change):
        """Update the value of COMPSET_LNAME based on the current values of COMP_???_PHYS and COMP_???_OPTION variables.
        This is done every time COMP_???_PHYS or COMP_???_OPTION variables are (re-)assigned."""
        if cvars["COMPSET_MODE"].value != "Custom":
            return # When in Standard mode, COMPSET_LNAME is set by another observer
        if any(cvars[f"COMP_{comp_class}_PHYS"].value == None for comp_class in cime.comp_classes):
            cvars["COMPSET_LNAME"].value = None
        else:
            compset_lname = cvars['INITTIME'].value
            for comp_class in cime.comp_classes:
                opt = cvars[f'COMP_{comp_class}_OPTION'].value
                compset_lname += '_'+cvars[f'COMP_{comp_class}_PHYS'].value
                compset_lname += '' if opt is None or opt=="(none)" else '%'+opt
            cvars["COMPSET_LNAME"].value = compset_lname

    # Register observers
    for comp_class in cime.comp_classes:
        cvars[f"COMP_{comp_class}_PHYS"].observe(
            update_compset_lname,
            names="value",
            type="change",
        )
        cvars[f"COMP_{comp_class}_OPTION"].observe(
            update_compset_lname,
            names="value",
            type="change",
        )