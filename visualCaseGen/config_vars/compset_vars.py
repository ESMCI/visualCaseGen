"""Module to define and register ConfigVars"""

import logging
from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.config_var_str_ms import ConfigVarStrMS

logger = logging.getLogger("\t" + __name__.split(".")[-1])

def initialize_compset_variables(cime):

    ConfigVarStr("COMPSET_MODE") # Standard or Custom

    initialize_standard_compset_variables(cime)
    initialize_custom_compset_variables(cime)

@owh.out.capture()
def initialize_standard_compset_variables(cime):

    # COMPSET Support Level: "All" or Scientifically "Supported" Only
    cv_support_level = ConfigVarStr("SUPPORT_LEVEL")

    @owh.out.capture()
    def support_level_tracker(change):
        """If the support level is changed to Supported, then set all component filters to 'any'.
        automatically since we have a very limited list of scientifically supported compsets."""
        new_support_level = change["new"]
        if new_support_level == "Supported":
            for comp_class in cime.comp_classes:
                cvars[f"COMP_{comp_class}_FILTER"].value = "any"
        else:
            for comp_class in cime.comp_classes:
                cvars[f"COMP_{comp_class}_FILTER"].value = None
    
    cv_support_level.observe(support_level_tracker, names="value", type="change")
 
    # Component Filters that the user can apply to narrow down the list of compsets
    for comp_class in cime.comp_classes:
        ConfigVarStr(
            name = f"COMP_{comp_class}_FILTER",
            default_value = "any",
        )

    # Compset Alias
    cv_compset_alias = ConfigVarStrMS("COMPSET_ALIAS")

    def reset_all_comp_vars():
        """Reset all component variables to None. This gets called every time the compset alias is changed."""
        if cvars['COMPSET_LNAME'].value is not None:
            cvars['COMPSET_LNAME'].value = None
        for comp_class in cime.comp_classes:
            if cvars[f'COMP_{comp_class}'].value is not None:
                cvars[f'COMP_{comp_class}'].value = None
            if cvars[f'COMP_{comp_class}_PHYS'].value is not None:
                cvars[f'COMP_{comp_class}_PHYS'].value = None
            if cvars[f'COMP_{comp_class}_OPTION'].value is not None:
                cvars[f'COMP_{comp_class}_OPTION'].value = None

    @owh.out.capture()
    def compset_alias_tracker(change):
        """If the compset alias is changed, then set the compset lname automatically."""
        new_compset_alias = change['new']
        reset_all_comp_vars()
        if new_compset_alias not in [None, ()]:
            new_compset_lname = cime.compsets[new_compset_alias].lname
            compset_lname_parts = cime.get_components_from_compset_lname(new_compset_lname)
            for comp_class in cime.comp_classes:
                compset_lname_x = compset_lname_parts.get(comp_class, None)
                assert compset_lname_x is not None, f"Component for {comp_class} not found in {new_compset_lname}"
                phys = compset_lname_x.split("%")[0]
                opt = compset_lname_x.split("%")[1] if "%" in compset_lname_x else None
                cvars[f'COMP_{comp_class}'].value = next((model for model in cime.models[comp_class] if phys in cime.comp_phys[model]))
                cvars[f'COMP_{comp_class}_PHYS'].value = phys
                cvars[f'COMP_{comp_class}_OPTION'].value = opt
            cvars['COMPSET_LNAME'].value = new_compset_lname


    cv_compset_alias.observe(compset_alias_tracker, names="value", type="change")


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