"""Unit tests for Stage.relevance_condition: stages that are irrelevant under the
current configuration are auto-skipped (not shown), while their variables are still
resolved so downstream logic stays well-defined.

These tests build a tiny stage tree by hand with a minimal fake widget, so they exercise
only the ProConPy stage/CSP machinery (no CIME / GUI stack required)."""

from z3 import Implies
from ProConPy.config_var import ConfigVar, cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.stage import Stage
from ProConPy.csp_solver import csp


class _FakeStageWidget:
    """Minimal stand-in for StageWidget exercising only what Stage calls on its widget."""

    def __init__(self):
        self._stage = None

    @property
    def stage(self):
        return self._stage

    @stage.setter
    def stage(self, value):
        self._stage = value

    def add_child_stages(self, first_child=None):
        pass

    def remove_child_stages(self):
        pass


def _build():
    """Build the stage chain: Select -> A -> B -> C, where B is relevant iff DRIVER=='on'.

    A relational constraint forces B's variable to a single option exactly when DRIVER=='off'
    (i.e., when B is irrelevant), mirroring how the real component-grid stages become fully
    determined for stub/data components."""
    ConfigVar.reboot()
    Stage.reboot()

    cv_driver = ConfigVarStr("DRIVER")
    cv_a = ConfigVarStr("A_VAL")
    cv_b = ConfigVarStr("B_VAL")
    cv_c = ConfigVarStr("C_VAL")

    Stage("Select", "select", widget=_FakeStageWidget(), varlist=[cv_driver])
    stg_a = Stage("A", "a", widget=_FakeStageWidget(), varlist=[cv_a], parent=Stage.first())
    stg_b = Stage(
        "B", "b", widget=_FakeStageWidget(), varlist=[cv_b], parent=stg_a,
        relevance_condition=(cvars["DRIVER"] == "on"),
    )
    Stage("C", "c", widget=_FakeStageWidget(), varlist=[cv_c], parent=stg_b)

    constraints = {
        Implies(cvars["DRIVER"] == "off", cvars["B_VAL"] == "b1"): "B is forced when driver is off",
    }
    csp.initialize(cvars, constraints, Stage.first())

    cv_driver.options = ["on", "off"]
    cv_a.options = ["a1", "a2"]
    cv_b.options = ["b1", "b2"]
    cv_c.options = ["c1", "c2"]

    return cv_driver, cv_a, cv_b, cv_c


def test_irrelevant_stage_is_skipped_and_resolved():
    cv_driver, cv_a, cv_b, cv_c = _build()
    assert Stage.active().title == "Select"
    cv_driver.value = "off"
    assert Stage.active().title == "A"
    cv_a.value = "a1"
    # B is irrelevant (DRIVER='off'): it is skipped and traversal lands on C.
    assert Stage.active().title == "C"
    # B's variable is still auto-resolved to its single valid option.
    assert cv_b.value == "b1"


def test_relevant_stage_is_shown():
    cv_driver, cv_a, cv_b, cv_c = _build()
    cv_driver.value = "on"
    cv_a.value = "a1"
    # B is relevant (DRIVER='on') and under-determined: it stays active for the user.
    assert Stage.active().title == "B"
    cv_b.value = "b1"
    assert Stage.active().title == "C"


def test_revert_skips_back_over_skipped_stage():
    cv_driver, cv_a, cv_b, cv_c = _build()
    cv_driver.value = "off"
    cv_a.value = "a1"
    assert Stage.active().title == "C"
    assert cv_b.value == "b1"
    # Reverting from C must skip back over the auto-skipped B and land on A.
    Stage.active().revert()
    assert Stage.active().title == "A"
    # The auto-set value of the skipped stage is cleared on the way back.
    assert cv_b.value is None
    assert cv_c.value is None


def test_stage_reappears_after_reconfiguration():
    cv_driver, cv_a, cv_b, cv_c = _build()
    cv_driver.value = "off"
    cv_a.value = "a1"
    assert Stage.active().title == "C"
    Stage.active().revert()  # back to A
    Stage.active().revert()  # back to Select
    assert Stage.active().title == "Select"
    # Reconfiguring the driver to 'on' makes B relevant again.
    cv_driver.value = "on"
    cv_a.value = "a2"
    assert Stage.active().title == "B"
