from ipywidgets import VBox, ToggleButtons
from z3 import Contains, Implies
from ProConPy.config_var import ConfigVar, cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.config_var_str_ms import ConfigVarStrMS
from ProConPy.stage import Stage
from ProConPy.csp_solver import csp
from visualCaseGen.custom_widget_types.multi_checkbox import MultiCheckbox
from visualCaseGen.custom_widget_types.stage_widget import StageWidget


def test_multiple_options_with_constraint():
    """A multi-select variable can hold several of its options at once, e.g. "REGIONAL%MARBL-BIO",
    and relational constraints still see each of them."""
    ConfigVar.reboot()
    Stage.reboot()

    cv_model = ConfigVarStr("MODEL")
    cv_model.widget = ToggleButtons()
    cv_opt = ConfigVarStrMS("OPT")
    cv_opt.widget = MultiCheckbox()
    cv_grid = ConfigVarStr("GRID")
    cv_grid.widget = ToggleButtons()

    # As with COMP_OCN_OPTION, OPT's options are registered in a stage before OPT's own.
    Stage("Model", "model", widget=StageWidget(VBox), varlist=[cv_model])
    stg_opt = Stage(
        "Options",
        "options",
        widget=StageWidget(VBox),
        varlist=[cv_opt],
        parent=Stage.first(),
    )
    Stage("Grid", "grid", widget=StageWidget(VBox), varlist=[cv_grid], parent=stg_opt)

    constraints = {Implies(Contains(cv_opt, "b"), cv_grid == "g_b"): "b requires g_b"}
    csp.initialize(cvars, constraints, Stage.first())

    cv_model.options = ["m1", "m2"]
    cv_opt.options = ["(none)", "a", "b"]
    cv_grid.options = ["g_a", "g_b"]

    cv_model.value = "m1"
    cv_opt.value = "a%b"
    assert cv_opt.value == "a%b"

    # The constraint on the second option leaves g_b as the only valid grid.
    assert cv_grid._options_validities == {"g_a": False, "g_b": True}
