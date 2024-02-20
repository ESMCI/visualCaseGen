from ProConPy.config_var import cvars
from ProConPy.options_spec import OptionsSpec

def set_options(cime):

    cv_compset_mode = cvars["COMPSET_MODE"]
    cv_compset_mode.options = ["Standard", "Custom"]
    cv_compset_mode.tooltips = ["Select from a list of predefined compsets", 
                            "Construct a custom compset"]

    cv_inittime = cvars["INITTIME"]
    cv_inittime.options = ["1850", "2000", "HIST"]
    cv_inittime.tooltips = ["Pre-industrial", "Present day", "Historical"]

    for comp_class in cime.comp_classes:
        cv_comp = cvars[f"COMP_{comp_class}"]
        cv_comp.options = [model for model in cime.models[comp_class] if model[0] != "x"]

        cv_comp_phys = cvars[f"COMP_{comp_class}_PHYS"]
        cv_comp_phys.options_spec = OptionsSpec(
            func = lambda model: (cime.comp_phys[model], cime.comp_phys_desc[model]), 
            args = (cv_comp,)
        )

        cv_comp_option = cvars[f"COMP_{comp_class}_OPTION"]
        cv_comp_option.options_spec = OptionsSpec(
            func = lambda phys: (["(none)"] + cime.comp_options[phys], ["no modifiers"] + cime.comp_options_desc[phys]), 
            args = (cv_comp_phys,)
        )


    cv_grid_mode = cvars["GRID_MODE"]
    cv_grid_mode.options = ["Standard", "Custom"]
    cv_grid_mode.tooltips = ["Select from a list of predefined grids", 
                            "Construct a custom compset"]
