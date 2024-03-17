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

    cv_grid_mode = cvars["GRID_MODE"]
    cv_grid_mode.options = ["Standard", "Custom"]
    cv_grid_mode.tooltips = [
        "Select from a list of predefined grids",
        "Construct a custom compset",
    ]

    set_standard_compset_options(cime)
    set_custom_compset_options(cime)
    set_standard_grid_options(cime)
    set_custom_grid_options(cime)
    set_launcher_options(cime)


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


def set_standard_grid_options(cime):

    def grid_options_func(compset_lname, grid_mode):

        if grid_mode != "Standard":
            return None, None

        compatible_grids = []
        grid_descriptions = []
        support_level = cvars["SUPPORT_LEVEL"].value
        compset_alias = cvars["COMPSET_ALIAS"].value

        assert (
            support_level != "Supported" or compset_alias is not None
        ), "Support level is 'Supported', but no compset alias is selected."

        for alias, compset_attr, not_compset_attr, desc in cime.resolutions:
            if (
                support_level == "Supported"
                and alias not in cime.sci_supported_grids[compset_alias]
            ):
                continue
            if compset_attr and not re.search(compset_attr, compset_lname):
                continue
            if not_compset_attr and re.search(not_compset_attr, compset_lname):
                continue

            grid_lname_parts = cime.get_grid_lname_parts(alias, compset_lname)

            try:
                csp.check_assignments(
                    (
                        (cvars["ATM_GRID"], grid_lname_parts["a%"]),
                        (cvars["LND_GRID"], grid_lname_parts["l%"]),
                        (cvars["OCN_GRID"], grid_lname_parts["oi%"]),
                        (cvars["ICE_GRID"], grid_lname_parts["oi%"]),
                        (cvars["ROF_GRID"], grid_lname_parts["r%"]),
                        (cvars["GLC_GRID"], grid_lname_parts["g%"]),
                        (cvars["WAV_GRID"], grid_lname_parts["w%"]),
                        (cvars["MASK_GRID"], grid_lname_parts["m%"]),
                    )
                )
            except ConstraintViolation:
                continue

            compatible_grids.append(alias)
            grid_descriptions.append(desc)

        return compatible_grids, grid_descriptions

    cv_grid = cvars["GRID"]
    cv_grid.options_spec = OptionsSpec(
        func=grid_options_func, args=([cvars[f"COMPSET_LNAME"], cvars["GRID_MODE"]])
    )


def set_custom_grid_options(cime):

    cv_custom_atm_grid = cvars["CUSTOM_ATM_GRID"]
    cv_custom_atm_grid.options = [
        "T62",
        "TL319",
        "0.9x1.25",
        "1.9x2.5",
        "4x5",
        "ne30np4",
        "ne60np4",
        "ne120np4",
    ]
    cv_custom_atm_grid.tooltips = [
        "T62 Gaussian Grid",
        "JRA55 datm grid",
        "FV 1-deg grid",
        "FV 2-deg grid",
        "FV 4-deg grid",
        "Spectral Elem 1-deg grid",
        "Spectral Elem 1/2-deg grid",
        "Spectral Elem 1/4-deg grid",
    ]

    cv_custom_ocn_grid_mode = cvars["OCN_GRID_MODE"]
    cv_custom_ocn_grid_mode.options = ["Standard", "Modify Existing", "Create New"]
    cv_custom_ocn_grid_mode.tooltips = [
        "Select from a list of existing MOM6 grids",
        "Modify an existing MOM6 grid",
        "Construct a new custom MOM6 grid",
    ]

    def custom_ocn_grid_options_func(comp_ocn_phys, custom_atm_grid):

        if comp_ocn_phys == "DOCN":
            return [custom_atm_grid], [
                "(When DOCN is selected, custom OCN grid is automatically set to ATM grid.)"
            ]
        else:
            compatible_ocn_grids = []
            descriptions = []
            for ocn_grid in cime.component_grids["ocnice"]:
                try:
                    csp.check_assignment(cvars["OCN_GRID"], ocn_grid)
                except ConstraintViolation:
                    continue
                compatible_ocn_grids.append(ocn_grid)
                descriptions.append(cime.domains_desc.get(ocn_grid) or "")

            return compatible_ocn_grids, descriptions

    cv_custom_ocn_grid = cvars["CUSTOM_OCN_GRID"]
    cv_custom_ocn_grid.options_spec = OptionsSpec(
        func=custom_ocn_grid_options_func,
        args=(cvars["COMP_OCN_PHYS"], cvars["CUSTOM_ATM_GRID"]),
    )

    cv_ocn_grid_extent = cvars["OCN_GRID_EXTENT"]
    cv_ocn_grid_extent.options = ["Global", "Regional"]
    cv_ocn_grid_extent.tooltips = ["Global ocean grid", "Regional ocean grid"]

    cv_ocn_cyclic_x = cvars["OCN_CYCLIC_X"]
    cv_ocn_cyclic_x.options = ["Yes", "No"]
    cv_ocn_cyclic_x.tooltips = ["Cyclic in x-direction", "Non-cyclic in x-direction"]


def set_launcher_options(cime):

    cv_machine = cvars["MACHINE"]
    cv_machine.options = cime.machines
