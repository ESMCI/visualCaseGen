from ipywidgets import Widget
import shutil
from pathlib import Path
from ProConPy.config_var import ConfigVar

def frontend_change(cvar, new_val):
    """This method simulates a frontend value change for a widget. It is useful for testing purposes."""

    assert isinstance(cvar, ConfigVar), "cvar must be an instance of ConfigVar"
    widget = cvar._widget
    assert isinstance(widget, Widget), "widget must be an instance of ipywidgets.Widget"

    widget.value = new_val

    # acquire and release the lock to simulate a frontend change
    widget._property_lock = {"value": widget.value}
    widget._property_lock = {}


def safe_create_case(srcroot, case_creator):
    """This method safely creates a case using the CaseCreator widget. It backs up the ccs_config 
    xml files before creating the case and restores them after the case is created. This is useful
    for testing purposes."""

    try:
        # back up ccs_config xml files to be modified
        shutil.copy(
            Path(srcroot) / "ccs_config/modelgrid_aliases_nuopc.xml",
            Path(srcroot) / "ccs_config/modelgrid_aliases_nuopc.xml.bak",
        )
        shutil.copy(
            Path(srcroot) / "ccs_config/component_grids_nuopc.xml",
            Path(srcroot) / "ccs_config/component_grids_nuopc.xml.bak",
        )

        # Click the create_case button
        case_creator._create_case()

    finally:
        # Restore ccs_config xml files
        shutil.move(
            Path(srcroot) / "ccs_config/modelgrid_aliases_nuopc.xml.bak",
            Path(srcroot) / "ccs_config/modelgrid_aliases_nuopc.xml",
        )
        shutil.move(
            Path(srcroot) / "ccs_config/component_grids_nuopc.xml.bak",
            Path(srcroot) / "ccs_config/component_grids_nuopc.xml",
        )
