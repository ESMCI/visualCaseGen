import sys
from z3 import Implies, Concat, If
from visualCaseGen.logic_utils import In
from visualCaseGen.dev_utils import RunError
import re

sys.path.append("../")


class OptionsSpec:
    def __init__(
        self,
        var,
        options_and_tooltips=None,
        options_and_tooltips_static=None,
        options_and_tooltips_dynamic=None,
        inducing_vars=[],
    ):
        self.var = var
        self.var.options_spec = self

        self.options_and_tooltips_static = None  # to be used in static mode only
        self.options_and_tooltips_dynamic = None  # to be used in dynamic mode only

        if options_and_tooltips is not None:
            assert (
                options_and_tooltips_static is None
                and options_and_tooltips_dynamic is None
            ), "If options_and_tooltips is provided, do not provide separate static and dynamic versions"
            assert isinstance(options_and_tooltips, tuple)

            self.options_and_tooltips_static = options_and_tooltips
            self.options_and_tooltips_dynamic = lambda: options_and_tooltips

        else:
            assert (
                options_and_tooltips_static is not None
                and options_and_tooltips_dynamic is not None
            ), "If options_and_tooltips is not provided, provide separate static and dynamic versions"
            assert isinstance(options_and_tooltips_static, (tuple, dict))
            assert callable(options_and_tooltips_dynamic)

            self.options_and_tooltips_static = options_and_tooltips_static
            self.options_and_tooltips_dynamic = options_and_tooltips_dynamic

        self.var.assign_options_spec(self)

        assert isinstance(inducing_vars, list), "inducing_vars parameter must be a list"
        self.inducing_vars = inducing_vars

    def __call__(self):
        # returns the list of options. Used in dynamic mode only.

        if any([inducing_var.is_none() for inducing_var in self.inducing_vars]):
            return None, None

        options, tooltips = self.options_and_tooltips_dynamic(
            *(var.value for var in self.inducing_vars)
        )
        return options, tooltips

    def has_propositioned_options(self):
        """Returns True if options_and_tooltips is propositioned (nested). Used in static mode only."""
        if isinstance(
            self.options_and_tooltips_static, tuple
        ):  # single options list with no propositions
            return False
        elif isinstance(
            self.options_and_tooltips_static, dict
        ):  # multiple options list with propsitions
            return True
        else:
            raise RunError(
                "Unknown options list type encountered in an OptionsSpec instance."
            )

    def has_inducing_vars(self):
        return len(self.inducing_vars) > 0

    def get_options(self):
        """Returns all options with all propositions. Used in static mode only"""
        options = []
        if self.has_propositioned_options():
            for (
                proposition,
                options_and_tooltips,
            ) in self.options_and_tooltips_static.items():
                options.extend(options_and_tooltips[0])
        else:
            options.extend(self.options_and_tooltips_static[0])
        return options

    def get_options_assertions(self):
        """Returns all options assertions. Used in static mode only."""
        assertions = None
        if self.has_propositioned_options():
            assertions = [
                Implies(proposition, In(self.var, options_and_tooltips[0]))
                for proposition, options_and_tooltips in self.options_and_tooltips_static.items()
            ]
        else:
            assertions = [In(self.var, self.options_and_tooltips_static[0])]
        return assertions

    def write_all_options_specs(cvars, filename):
        with open(filename, "w") as file:
            for varname, var in cvars.items():
                if hasattr(var, "options_spec"):
                    assertions = var._options_spec.get_options_assertions()
                    for assertion in assertions:
                        file.write(str(assertion))
                        file.write("\n")


def get_options_specs(cvars, ci):

    # INITTIME
    INITTIME = cvars["INITTIME"]
    OptionsSpec(
        var=INITTIME,
        options_and_tooltips=(
            ["1850", "2000", "HIST"],
            ["Pre-industrial", "Present day", "Historical"],
        ),
    )

    # COMP_???
    for comp_class in ci.comp_classes:
        COMP = cvars[f"COMP_{comp_class}"]
        OptionsSpec(
            var=COMP,
            options_and_tooltips=(
                [model for model in ci.models[comp_class] if model[0] != "x"],
                None,
            ),
        )

    # COMP_???_PHYS
    for comp_class in ci.comp_classes:
        COMP = cvars[f"COMP_{comp_class}"]
        COMP_PHYS = cvars[f"COMP_{comp_class}_PHYS"]
        OptionsSpec(
            var=COMP_PHYS,
            options_and_tooltips_static={
                COMP == model: (ci.comp_phys[model], ci.comp_phys_desc[model])
                for model in ci.models[comp_class]
                if model[0] != "x"
            },
            options_and_tooltips_dynamic=lambda model: (
                ci.comp_phys[model],
                ci.comp_phys_desc[model],
            ),
            inducing_vars=[COMP],
        )

    # COMP_???_OPTION
    for comp_class in ci.comp_classes:
        COMP = cvars[f"COMP_{comp_class}"]
        COMP_PHYS = cvars[f"COMP_{comp_class}_PHYS"]
        COMP_OPTION = cvars[f"COMP_{comp_class}_OPTION"]
        OptionsSpec(
            var=COMP_OPTION,
            options_and_tooltips_static={
                COMP_PHYS
                == phys: (
                    ["(none)"] + ci.comp_options[phys],
                    ["no modifiers"] + ci.comp_options_desc[phys],
                )
                for model in ci.models[comp_class]
                if model[0] != "x"
                for phys in ci.comp_phys[model]
            },
            options_and_tooltips_dynamic=lambda phys: (
                ["(none)"] + ci.comp_options[phys],
                ["no modifiers"] + ci.comp_options_desc[phys],
            ),
            inducing_vars=[COMP_PHYS],
        )

    # COMPSET

    def compset_func(*args):

        new_compset_text = cvars["INITTIME"].value

        for comp_class in ci.comp_classes:

            # Component Physics:
            cv_comp_phys = cvars["COMP_{}_PHYS".format(comp_class)]
            if cv_comp_phys.is_none():
                return [
                    ""
                ]  # not all component physics selected yet, so not ready to set COMPSET

            comp_phys_val = cv_comp_phys.value
            if comp_phys_val == "Specialized":
                comp_phys_val = "CAM"  # todo: generalize this special case
            new_compset_text += "_" + comp_phys_val

            # Component Option (optional)
            cv_comp_option = cvars["COMP_{}_OPTION".format(comp_class)]
            if cv_comp_option.is_none():
                return [
                    ""
                ]  # not all component options selected yet, so not ready to set COMPSET

            comp_option_val = cv_comp_option.value
            new_compset_text += "%" + comp_option_val

        new_compset_text = new_compset_text.replace("%(none)", "")
        return [new_compset_text], None

    COMPSET = cvars["COMPSET"]
    COMP_ATM_PHYS = cvars["COMP_ATM_PHYS"]
    COMP_ATM_OPTION = cvars["COMP_ATM_OPTION"]
    COMP_LND_PHYS = cvars["COMP_LND_PHYS"]
    COMP_LND_OPTION = cvars["COMP_LND_OPTION"]
    COMP_ICE_PHYS = cvars["COMP_ICE_PHYS"]
    COMP_ICE_OPTION = cvars["COMP_ICE_OPTION"]
    COMP_OCN_PHYS = cvars["COMP_OCN_PHYS"]
    COMP_OCN_OPTION = cvars["COMP_OCN_OPTION"]
    COMP_ROF_PHYS = cvars["COMP_ROF_PHYS"]
    COMP_ROF_OPTION = cvars["COMP_ROF_OPTION"]
    COMP_GLC_PHYS = cvars["COMP_GLC_PHYS"]
    COMP_GLC_OPTION = cvars["COMP_GLC_OPTION"]
    COMP_WAV_PHYS = cvars["COMP_WAV_PHYS"]
    COMP_WAV_OPTION = cvars["COMP_WAV_OPTION"]
    OptionsSpec(
        var=COMPSET,
        options_and_tooltips_static=(
            [
                Concat(
                    INITTIME,
                    "_",
                    If(
                        COMP_ATM_OPTION == "(none)",
                        COMP_ATM_PHYS,
                        Concat(COMP_ATM_PHYS, "%", COMP_ATM_OPTION),
                    ),
                    "_",
                    If(
                        COMP_LND_OPTION == "(none)",
                        COMP_LND_PHYS,
                        Concat(COMP_LND_PHYS, "%", COMP_LND_OPTION),
                    ),
                    "_",
                    If(
                        COMP_ICE_OPTION == "(none)",
                        COMP_ICE_PHYS,
                        Concat(COMP_ICE_PHYS, "%", COMP_ICE_OPTION),
                    ),
                    "_",
                    If(
                        COMP_OCN_OPTION == "(none)",
                        COMP_OCN_PHYS,
                        Concat(COMP_OCN_PHYS, "%", COMP_OCN_OPTION),
                    ),
                    "_",
                    If(
                        COMP_ROF_OPTION == "(none)",
                        COMP_ROF_PHYS,
                        Concat(COMP_ROF_PHYS, "%", COMP_ROF_OPTION),
                    ),
                    "_",
                    If(
                        COMP_GLC_OPTION == "(none)",
                        COMP_GLC_PHYS,
                        Concat(COMP_GLC_PHYS, "%", COMP_GLC_OPTION),
                    ),
                    "_",
                    If(
                        COMP_WAV_OPTION == "(none)",
                        COMP_WAV_PHYS,
                        Concat(COMP_WAV_PHYS, "%", COMP_WAV_OPTION),
                    ),
                )
            ],
            None,
        ),
        options_and_tooltips_dynamic=compset_func,
        inducing_vars=[INITTIME]
        + [
            cvars["COMP_{}_OPTION".format(comp_class)] for comp_class in ci.comp_classes
        ],
    )

    # GRID
    GRID = cvars["GRID"]

    def grid_options_func(compset):

        if compset == "":
            return None, None

        compatible_grids = []
        grid_descriptions = []

        for alias, compset_attr, not_compset_attr, desc in ci.model_grids:
            if compset_attr and not re.search(compset_attr, compset):
                continue
            if not_compset_attr and re.search(not_compset_attr, compset):
                continue
            if GRID.view_mode == "suggested" and desc == "":
                continue

            comp_grid_dict = ci.retrieve_component_grids(alias, compset)

            try:
                cvars["ATM_GRID"].major_layer.check_assignment(
                    cvars["ATM_GRID"], comp_grid_dict["a%"]
                )
                cvars["LND_GRID"].major_layer.check_assignment(
                    cvars["LND_GRID"], comp_grid_dict["l%"]
                )
                cvars["OCN_GRID"].major_layer.check_assignment(
                    cvars["OCN_GRID"], comp_grid_dict["oi%"]
                )
                cvars["ICE_GRID"].major_layer.check_assignment(
                    cvars["ICE_GRID"], comp_grid_dict["oi%"]
                )
                cvars["ROF_GRID"].major_layer.check_assignment(
                    cvars["ROF_GRID"], comp_grid_dict["r%"]
                )
                cvars["GLC_GRID"].major_layer.check_assignment(
                    cvars["GLC_GRID"], comp_grid_dict["g%"]
                )
                cvars["WAV_GRID"].major_layer.check_assignment(
                    cvars["WAV_GRID"], comp_grid_dict["w%"]
                )
                cvars["MASK_GRID"].major_layer.check_assignment(
                    cvars["MASK_GRID"], comp_grid_dict["m%"]
                )
            except AssertionError:
                continue

            compatible_grids.append(alias)
            grid_descriptions.append(desc)

        return compatible_grids, grid_descriptions

    grid_opts = {}
    for alias, compset_attr, not_compset_attr, desc in ci.model_grids:
        if compset_attr is None and not_compset_attr is None:
            if not True in grid_opts:
                grid_opts[True] = ([], [])
            grid_opts[True][0].append(alias)
            grid_opts[True][1].append(desc)

        else:
            pass

    OptionsSpec(
        var=GRID,
        options_and_tooltips_static=grid_opts,
        options_and_tooltips_dynamic=grid_options_func,
        inducing_vars=[COMPSET],
    )


    # GRID_MODE
    GRID_MODE = cvars["GRID_MODE"]
    OptionsSpec(
        var=GRID_MODE,
        options_and_tooltips=(
            ['Predefined', 'Custom'],
            ['Select from the list of existing CESM grids', 'Create a new grid for one or more of the active components.'],
        ),
    )

    # OCN_GRID_EXTENT
    OCN_GRID_EXTENT = cvars["OCN_GRID_EXTENT"]
    OptionsSpec(
        var=OCN_GRID_EXTENT,
        options_and_tooltips=(
            ['Regional', 'Global'],
            ['Regional', 'Global'],
        ),
    )
    # OCN_GRID_CONFIG
    OCN_GRID_CONFIG = cvars["OCN_GRID_CONFIG"]
    OptionsSpec(
        var=OCN_GRID_CONFIG,
        options_and_tooltips=(
            ['Cartesian', 'Mercator', 'Spherical'],
            ['Cartesian', 'Mercator', 'Spherical'],
        ),
    )