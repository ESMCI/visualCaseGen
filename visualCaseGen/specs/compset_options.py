import re
from ProConPy.config_var import cvars
from ProConPy.options_spec import OptionsSpec
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.csp_solver import csp


def set_compset_options(cime):

    cv_compset_mode = cvars["COMPSET_MODE"]
    cv_compset_mode.options = ["Standard", "Custom"]
    cv_compset_mode.tooltips = [
        "Select from a list of predefined compsets",
        "Construct a custom compset",
    ]

    set_standard_compset_options(cime)
    set_custom_compset_options(cime)

def set_standard_compset_options(cime):

    cv_scientifically_supported = cvars["SUPPORT_LEVEL"]
    cv_scientifically_supported.options = ["All", "Supported"]
    cv_scientifically_supported.tooltips = [
        "All standard compsets",
        "Standard compsets that are scientifically supported, i.e., validated",
    ]

    for comp_class in cime.comp_classes:
        cv_comp_filter = cvars[f"COMP_{comp_class}_FILTER"]
        cv_comp_filter_options = ["any"]
        cv_comp_filter_options.extend(
            [
                model
                for model in cime.models[comp_class]
                if model[0] != "x" and model.upper() != "S" + comp_class
            ]
        )
        cv_comp_filter_options.append("none")
        cv_comp_filter.options = cv_comp_filter_options

    def compset_alias_options_func(
        support_level,
        atm_filter,
        lnd_filter,
        ice_filter,
        ocn_filter,
        rof_filter,
        glc_filter,
        wav_filter,
    ):

        filters = (
            ("ATM", atm_filter),
            ("LND", lnd_filter),
            ("ICE", ice_filter),
            ("OCN", ocn_filter),
            ("ROF", rof_filter),
            ("GLC", glc_filter),
            ("WAV", wav_filter),
        )

        # Determine available compset aliases. Take support level and filters into account
        available_compsets = [
            compset
            for compset in cime.compsets.values()
            if (
                support_level == "All"
                and all(
                    [
                        comp_filter == "any"
                        or comp_filter.upper() in compset.lname
                        or (
                            comp_filter == "none"
                            and (
                                "S" + comp_class in compset.lname
                                or "X" + comp_class in compset.lname
                            )
                        )
                        for comp_class, comp_filter in filters
                    ]
                )
            )
            or (
                support_level == "Supported"
                and len(cime.sci_supported_grids[compset.alias]) > 0
            )
        ]

        available_compset_aliases = [ac.alias for ac in available_compsets]
        available_compset_descriptions = [
            cime.long_compset_desc(ac) for ac in available_compsets
        ]
        return available_compset_aliases, available_compset_descriptions

    cv_compset_alias = cvars["COMPSET_ALIAS"]
    cv_compset_alias.options_spec = OptionsSpec(
        func=compset_alias_options_func,
        args=[
            cvars["SUPPORT_LEVEL"],
            cvars["COMP_ATM_FILTER"],
            cvars["COMP_LND_FILTER"],
            cvars["COMP_ICE_FILTER"],
            cvars["COMP_OCN_FILTER"],
            cvars["COMP_ROF_FILTER"],
            cvars["COMP_GLC_FILTER"],
            cvars["COMP_WAV_FILTER"],
        ],
    )


def set_custom_compset_options(cime):

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
            func=lambda model: (
                (cime.comp_phys[model], cime.comp_phys_desc[model])
                if cvars["COMPSET_MODE"].value == "Custom"
                else (None, None)
            ),
            args=(cv_comp,),
        )

        cv_comp_option = cvars[f"COMP_{comp_class}_OPTION"]
        cv_comp_option.options_spec = OptionsSpec(
            func=lambda phys: (
                (
                    ["(none)"] + cime.comp_options[phys],
                    ["no modifiers"] + cime.comp_options_desc[phys],
                )
                if cvars["COMPSET_MODE"].value == "Custom"
                else (None, None)
            ),
            args=(cv_comp_phys,),
        )

