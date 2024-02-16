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

    #    cv_comp_phys = cvars[f"COMP_{comp_class}_PHYS"]
    #    cv_comp_phys.options = lambda: [cime.comp_phys[cv_comp.value]]
    #    cv_comp_phys.tooltips = lambda: [cime.comp_phys_desc[cv_comp.value]]

    #    #cv_comp_phys.options = [cime.comp_phys[model] for model in cime.models[comp_class] if model[0] != "x"]
    #    #cv_comp_phys.tooltips = [cime.comp_phys_desc[model] for model in cime.models[comp_class] if model[0] != "x"]


    ## COMP_???_PHYS
    #for comp_class in ci.comp_classes:
    #    COMP = cvars[f"COMP_{comp_class}"]
    #    COMP_PHYS = cvars[f"COMP_{comp_class}_PHYS"]
    #    OptionsSpec(
    #        var=COMP_PHYS,
    #        options_and_tooltips_static={
    #            COMP == model: (ci.comp_phys[model], ci.comp_phys_desc[model])
    #            for model in ci.models[comp_class]
    #            if model[0] != "x"
    #        },
    #        options_and_tooltips_dynamic=lambda model: (
    #            ci.comp_phys[model],
    #            ci.comp_phys_desc[model],
    #        ),
    #        inducing_vars=[COMP],
    #    )



    cv_grid_mode = cvars["GRID_MODE"]
    cv_grid_mode.options = ["Standard", "Custom"]
    cv_grid_mode.tooltips = ["Select from a list of predefined grids", 
                            "Construct a custom compset"]
