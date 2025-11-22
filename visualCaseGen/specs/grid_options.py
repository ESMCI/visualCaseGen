import re
from ProConPy.config_var import cvars
from ProConPy.options_spec import OptionsSpec
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.csp_solver import csp, unsat

def set_grid_options(cime):

    cv_grid_mode = cvars["GRID_MODE"]
    cv_grid_mode.options = ["Standard", "Custom"]
    cv_grid_mode.tooltips = [
        "Select from a list of predefined grids",
        "Construct a custom compset",
    ]

    set_standard_grid_options(cime)
    set_custom_atm_grid_options(cime)
    set_custom_ocn_grid_options(cime)
    set_custom_lnd_grid_options(cime)
    set_custom_rof_grid_options(cime)


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

        comp_grid_vars = [
            cvars["ATM_GRID"],
            cvars["LND_GRID"],
            cvars["OCN_GRID"],
            cvars["ICE_GRID"],
            cvars["ROF_GRID"],
            cvars["GLC_GRID"],
            cvars["WAV_GRID"],
            cvars["MASK_GRID"],
        ]

        with csp._solver as s:

            csp.apply_assignment_assertions(s, exclude_vars=comp_grid_vars)
            csp.apply_options_assertions(s, exclude_vars=comp_grid_vars)

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

                if s.check([
                    cvars["ATM_GRID"] == grid_lname_parts["a%"],
                    cvars["LND_GRID"] == grid_lname_parts["l%"],
                    cvars["OCN_GRID"] == grid_lname_parts["oi%"],
                    cvars["ICE_GRID"] == grid_lname_parts["oi%"],
                    cvars["ROF_GRID"] == grid_lname_parts["r%"],
                    cvars["GLC_GRID"] == grid_lname_parts["g%"],
                    cvars["WAV_GRID"] == grid_lname_parts["w%"],
                    cvars["MASK_GRID"] == grid_lname_parts["m%"],
                ]) == unsat:
                    continue # Skip this grid if it is deemed invalid by the CSP solver

                compatible_grids.append(alias)
                grid_descriptions.append(desc)

        return compatible_grids, grid_descriptions

    cv_grid = cvars["GRID"]
    cv_grid.options_spec = OptionsSpec(
        func=grid_options_func, args=([cvars[f"COMPSET_LNAME"], cvars["GRID_MODE"]])
    )


def check_comp_grid(comp_class, proposed_grid, compset_lname):
    """Auxiliary function that checks if the proposed grid is compatible with the compset/not_compset
    constraints as well as the csp constraints."""

    if proposed_grid.compset_constr and not re.search(
        proposed_grid.compset_constr, compset_lname
    ):
        return False
    if proposed_grid.not_compset_constr and re.search(
        proposed_grid.not_compset_constr, compset_lname
    ):
        return False

    return csp.check_expression(cvars[f"{comp_class}_GRID"] == proposed_grid.name)


def set_custom_atm_grid_options(cime):
    """Set the options and options specs for the custom ATM grid variable.
    This function is called at initialization."""

    # CUSTOM_ATM_GRID options
    def custom_atm_grid_options_func(grid_mode):
        """Return the options and descriptions for the custom ATM grid variable."""

        if grid_mode != "Custom":
            return None, None

        compset_lname = cvars["COMPSET_LNAME"].value
        compatible_atm_grids = []
        descriptions = []
        for atm_grid in cime.domains["atm"].values():
            if check_comp_grid("ATM", atm_grid, compset_lname) is False:
                continue
            compatible_atm_grids.append(atm_grid.name)
            descriptions.append(atm_grid.desc)
        return compatible_atm_grids, descriptions

    cv_custom_atm_grid = cvars["CUSTOM_ATM_GRID"]
    cv_custom_atm_grid.options_spec = OptionsSpec(
        func=custom_atm_grid_options_func, args=(cvars["GRID_MODE"],)
    )


def set_custom_ocn_grid_options(cime):
    """Set the options and options specs for the custom OCN grid variables.
    This function is called at initialization."""

    # OCN_GRID_MODE options
    cv_custom_ocn_grid_mode = cvars["OCN_GRID_MODE"]
    cv_custom_ocn_grid_mode.options = ["Standard", "Create New"] # TODO: add "Modify Existing" option.
    cv_custom_ocn_grid_mode.tooltips = [
        "Select from a list of existing MOM6 grids",
        "Modify an existing MOM6 grid",
        "Construct a new custom MOM6 grid",
    ]

    # CUSTOM_OCN_GRID options
    def custom_ocn_grid_options_func(comp_ocn_phys, custom_atm_grid, ocn_grid_mode):
        """Return the options and descriptions for the custom OCN grid variable."""
        if ocn_grid_mode != "Standard":
            return None, None
        if comp_ocn_phys == "DOCN":
            return [custom_atm_grid], [
                "(When DOCN is selected, custom OCN grid is automatically set to ATM grid.)"
            ]
        else:
            compset_lname = cvars["COMPSET_LNAME"].value
            compatible_ocn_grids = []
            descriptions = []
            for ocn_grid in cime.domains["ocnice"].values():
                if check_comp_grid("OCN", ocn_grid, compset_lname) is False:
                    continue
                compatible_ocn_grids.append(ocn_grid.name)
                descriptions.append(ocn_grid.desc)

            return compatible_ocn_grids, descriptions

    cv_custom_ocn_grid = cvars["CUSTOM_OCN_GRID"]
    cv_custom_ocn_grid.options_spec = OptionsSpec(
        func=custom_ocn_grid_options_func,
        args=(cvars["COMP_OCN_PHYS"], cvars["CUSTOM_ATM_GRID"], cvars["OCN_GRID_MODE"]),
    )

    # OCN_GRID_EXTENT options
    cv_ocn_grid_extent = cvars["OCN_GRID_EXTENT"]
    cv_ocn_grid_extent.options = ["Global", "Regional"]
    cv_ocn_grid_extent.tooltips = ["Global ocean grid", "Regional ocean grid"]

    # OCN_CYCLIC_X options
    cv_ocn_cyclic_x = cvars["OCN_CYCLIC_X"]
    cv_ocn_cyclic_x.options = ["True", "False"]
    cv_ocn_cyclic_x.tooltips = ["Cyclic in x-direction", "Non-cyclic in x-direction"]

    # OCN_IC_MODE options
    cv_ocn_ic_mode = cvars["OCN_IC_MODE"]
    cv_ocn_ic_mode.options = ["Simple", "From File"]
    cv_ocn_ic_mode.tooltips = [
        "This corresponds to the MOM6 TS_CONFIG=fit and FIT_SALINITY=True configuration, "
        "where the surface temperature is set to a constant reference value and salinity "
        "is fit accordingly. This is rather a simple configuration and users are encouraged "
        "to further modify the initial conditions in the user_nl_mom6 file once the case is "
        "created.",
        "With this option, the initial temperature and salinity fields are read from a file.",
    ]

def set_custom_lnd_grid_options(cime):
    """Set the options and options specs for the custom LND grid variables."""

    # LND_GRID_MODE options
    cv_lnd_grid_mode = cvars["LND_GRID_MODE"]
    cv_lnd_grid_mode.options = ["Standard", "Modified"]
    cv_lnd_grid_mode.tooltips = [
        "Pick a standard land grid",
        "Modify an existing land grid",
    ]

    # CUSTOM_LND_GRID options
    def custom_lnd_grid_options_func(comp_lnd, custom_atm_grid, lnd_grid_mode):
        """Return the options and descriptions for the custom LND grid variable."""
        if comp_lnd != "clm":
            return [custom_atm_grid], [
                "(When CLM is not selected, custom LND grid is automatically set to ATM grid.)"
            ]
        else:
            compset_lname = cvars["COMPSET_LNAME"].value
            compatible_lnd_grids = []
            descriptions = []
            for lnd_grid in cime.domains["lnd"].values():
                if check_comp_grid("LND", lnd_grid, compset_lname) is False:
                    continue
                compatible_lnd_grids.append(lnd_grid.name)
                descriptions.append(lnd_grid.desc)
            return compatible_lnd_grids, descriptions

    cv_custom_lnd_grid = cvars["CUSTOM_LND_GRID"]
    cv_custom_lnd_grid.options_spec = OptionsSpec(
        func=custom_lnd_grid_options_func,
        args=(cvars["COMP_LND"], cvars["CUSTOM_ATM_GRID"], cvars["LND_GRID_MODE"]),
    )

    cv_fsurdat_idealized = cvars["FSURDAT_IDEALIZED"]
    cv_fsurdat_idealized.options = ["True", "False"]

    cv_lnd_include_nonveg = cvars["LND_INCLUDE_NONVEG"]
    cv_lnd_include_nonveg.options = ["True", "False"]


def set_custom_rof_grid_options(cime):
    """Set the options and options specs for the custom ROF grid variable.
    This function is called at initialization."""

    # CUSTOM_ROF_GRID options
    def custom_rof_grid_options_func(grid_mode):
        """Return the options and descriptions for the custom ROF grid variable."""

        if grid_mode != "Custom":
            return None, None
        
        if cvars["COMP_ROF"].value == "srof":
            return ["null"], ["(When stub ROF is selected, custom ROF grid is set to null.)"]

        # Loop through all ROF grids and check if they are compatible with the compset constraints
        compset_lname = cvars["COMPSET_LNAME"].value
        compatible_rof_grids = []
        descriptions = []
        for rof_grid in cime.domains["rof"].values():
            if check_comp_grid("ROF", rof_grid, compset_lname) is False:
                continue
            compatible_rof_grids.append(rof_grid.name)
            descriptions.append(rof_grid.desc)
        return compatible_rof_grids, descriptions

    cv_custom_rof_grid = cvars["CUSTOM_ROF_GRID"]
    cv_custom_rof_grid.options_spec = OptionsSpec(
        func=custom_rof_grid_options_func, args=(cvars["GRID_MODE"],)
    )