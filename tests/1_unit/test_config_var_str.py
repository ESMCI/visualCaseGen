import pytest
from traitlets import TraitError
from ipywidgets import VBox, Text
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.config_var import ConfigVar, cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.stage import Stage
from ProConPy.csp_solver import csp
from visualCaseGen.custom_widget_types.stage_widget import StageWidget
from tests.utils import frontend_change

def test_config_var_str():
    ConfigVar.reboot()
    Stage.reboot()

    cv_foo = ConfigVarStr("FOO", widget_none_val='', word_only=True)
    cv_foo.widget = Text()

    # Create a Main Stage object and initialize the csp solver
    Stage("MainStage", "Main Stage", widget=StageWidget(VBox), varlist=cvars.values())
    csp.initialize(cvars, {}, Stage.first())

    # set the initial value of the ConfigVarStr object
    cv_foo.value = "foo"

    # attempt to set the value of the ConfigVarStr object to a number
    with pytest.raises(TraitError) as excinfo:
        cv_foo.value = 1
    
    assert cv_foo.value == "foo" and cv_foo._widget.value == "foo"

    # attempt to set the value of the ConfigVarStr object to another string via frontend
    frontend_change(cv_foo, "bar")
    assert cv_foo.value == "bar" and cv_foo._widget.value == "bar"

    # confirm that only alphanumeric characters, underscore, and backslash are allowed 
    frontend_change(cv_foo, "bar!")
    assert cv_foo.value == "bar" and cv_foo._widget.value == "bar"

    # backslash and underscore are allowed
    frontend_change(cv_foo, "foo_bar/123")
    assert cv_foo.value == "foo_bar/123" and cv_foo._widget.value == "foo_bar/123"
