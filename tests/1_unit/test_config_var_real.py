import pytest
from traitlets import TraitError
from ipywidgets import VBox, Text
from ProConPy.config_var import ConfigVar, cvars
from ProConPy.config_var_real import ConfigVarReal
from ProConPy.stage import Stage
from ProConPy.csp_solver import csp
from visualCaseGen.custom_widget_types.stage_widget import StageWidget
from tests.utils import frontend_change

def test_config_var_real():
    ConfigVar.reboot()
    Stage.reboot()

    # Create a ConfigVarInt object
    cv_foo = ConfigVarReal("FOO")
    cv_foo.widget = Text()

    assert cv_foo.widget.continuous_update == False

    # Create a Main Stage object and initialize the csp solver
    Stage("MainStage", "Main Stage", widget=StageWidget(VBox), varlist=cvars.values())
    csp.initialize(cvars, {}, Stage.first())

    # set the initial value of the ConfigVarInt object
    cv_foo.value = 0.1

    # attempt to set the value of the ConfigVarInt object to a string
    with pytest.raises(TraitError) as excinfo:
        cv_foo.value = "foo"
    
    assert cv_foo.value == 0.1 and cv_foo._widget.value == "0.1"

    # attempt to set the value of the ConfigVarInt object to another number via frontend
    frontend_change(cv_foo, "-0.2")
    assert cv_foo.value == -0.2 and cv_foo._widget.value == "-0.2"

    # attempt to set the value of the ConfigVarInt object to a string via frontend
    frontend_change(cv_foo, "foo")

    # the widget value should not change when the value is invalid
    assert cv_foo.value == -0.2 and cv_foo._widget.value == "-0.2"