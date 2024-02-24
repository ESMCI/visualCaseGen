import re
from ProConPy.config_var import cvars
from ProConPy.options_spec import OptionsSpec
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.csp_solver import csp


def set_options(cime):

    cv_compset_mode = cvars["COMPSET_MODE"]
    cv_compset_mode.options = ["Standard", "Custom"]
    cv_compset_mode.tooltips = [
        "Select from a list of predefined compsets",
        "Construct a custom compset",
    ]

    cv_inittime = cvars["INITTIME"]
    cv_inittime.options = ["1850", "2000", "HIST"]
    cv_inittime.tooltips = ["Pre-industrial", "Present day", "Historical"]

    for comp_class in cime.comp_classes:
        cv_comp = cvars[f"COMP_{comp_class}"]
        cv_comp.options = [
            model for model in cime.models[comp_class] if model[0] != "x"
        ]

        cv_comp_phys = cvars[f"COMP_{comp_class}_PHYS"]
        cv_comp_phys.options_spec = OptionsSpec(
            func=lambda model: (cime.comp_phys[model], cime.comp_phys_desc[model]),
            args=(cv_comp,),
        )

        cv_comp_option = cvars[f"COMP_{comp_class}_OPTION"]
        cv_comp_option.options_spec = OptionsSpec(
            func=lambda phys: (
                ["(none)"] + cime.comp_options[phys],
                ["no modifiers"] + cime.comp_options_desc[phys],
            ),
            args=(cv_comp_phys,),
        )

    cv_grid_mode = cvars["GRID_MODE"]
    cv_grid_mode.options = ["Standard", "Custom"]
    cv_grid_mode.tooltips = [
        "Select from a list of predefined grids",
        "Construct a custom compset",
    ]

    def grid_options_func(compset_lname):

        if compset_lname == "":
            return None, None

        compatible_grids = []
        grid_descriptions = []

        for alias, compset_attr, not_compset_attr, desc in cime.model_grids:
            if compset_attr and not re.search(compset_attr, compset_lname):
                continue
            if not_compset_attr and re.search(not_compset_attr, compset_lname):
                continue
            if cvars["GRID"].view_mode == "suggested" and desc == "":
                continue

            grid_lname_parts = cime.get_grid_lname_parts(alias, compset_lname)

            try:
                csp.check_assignment(cvars["ATM_GRID"], grid_lname_parts["a%"])
                csp.check_assignment(cvars["LND_GRID"], grid_lname_parts["l%"])
                csp.check_assignment(cvars["OCN_GRID"], grid_lname_parts["oi%"])
                csp.check_assignment(cvars["ICE_GRID"], grid_lname_parts["oi%"])
                csp.check_assignment(cvars["ROF_GRID"], grid_lname_parts["r%"])
                csp.check_assignment(cvars["GLC_GRID"], grid_lname_parts["g%"])
                csp.check_assignment(cvars["WAV_GRID"], grid_lname_parts["w%"])
                csp.check_assignment(cvars["MASK_GRID"], grid_lname_parts["m%"])
            except ConstraintViolation:
                continue

            compatible_grids.append(alias)
            grid_descriptions.append(desc)

        return compatible_grids, grid_descriptions

    cv_grid = cvars["GRID"]
    cv_grid.options_spec = OptionsSpec(
        func=grid_options_func, args=(cvars["COMPSET_LNAME"],)
    )
