"""Module to define and register ConfigVars"""

import logging
from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.config_var_str_ms import ConfigVarStrMS

logger = logging.getLogger("\t" + __name__.split(".")[-1])


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

    @owh.out.capture()
    def compset_alias_tracker(change):
        """If the compset alias is changed, then set the compset lname automatically."""
        new_compset_alias = change['new']
        if new_compset_alias in [None, ()]:
            for comp_class in cime.comp_classes:
                cvars[f'COMP_{comp_class}_PHYS'].value = None
                cvars[f'COMP_{comp_class}_OPTION'].value = None
            cvars['COMPSET_LNAME'].value = None
        else:
            new_compset_lname = cime.compsets[new_compset_alias].lname
            compset_lname_parts = cime.get_components_from_compset_lname(new_compset_lname)
            for comp_class in cime.comp_classes:
                compset_lname_x = compset_lname_parts.get(comp_class, None)
                assert compset_lname_x is not None, f"Component for {comp_class} not found in {new_compset_lname}"
                cvars[f'COMP_{comp_class}_PHYS'].value = compset_lname_x.split("%")[0]
                cvars[f'COMP_{comp_class}_OPTION'].value = compset_lname_x.split("%")[1] if "%" in compset_lname_x else None
            cvars['COMPSET_LNAME'].value = new_compset_lname


    cv_compset_alias.observe(compset_alias_tracker, names="value", type="change")

