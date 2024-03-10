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

    # The auxiliary compset_lname variable is not directly controlled by the user:
    # it is automatically set every time:
    # (1) COMPSET_ALIAS is (re-)assigned, or
    # (2) all COMP_???_OPTION variables are (re-)assigned
    ConfigVarStr("COMPSET_LNAME")

    def compset_lname_updater(change):
        """Update the value of COMPSET_LNAME variable based on the selected component
        physics and options. This function is called automatically every time a
        COMP_???_OPTION variable is changed.
        """

        if any(
            cvars[f"COMP_{comp_class}_OPTION"].value == None
            for comp_class in cime.comp_classes
        ):
            cvars["COMPSET_LNAME"].value = None
        else:
            new_compset_lname = cvars["INITTIME"].value
            for comp_class in cime.comp_classes:
                # Component Physics:
                cv_comp_phys = cvars[f"COMP_{comp_class}_PHYS"]
                comp_phys_val = cv_comp_phys.value
                if comp_phys_val == "Specialized":
                    comp_phys_val = "CAM"
                new_compset_lname += "_" + comp_phys_val
                # Component Option (optional)
                cv_comp_option = cvars[f"COMP_{comp_class}_OPTION"]
                comp_option_val = cv_comp_option.value
                new_compset_lname += "%" + comp_option_val

            new_compset_lname = new_compset_lname.replace("%(none)", "")
            cvars["COMPSET_LNAME"].value = new_compset_lname

    for comp_class in cime.comp_classes:
        cvars[f"COMP_{comp_class}_OPTION"].observe(
            compset_lname_updater,
            names="value",
            type="change",
        )