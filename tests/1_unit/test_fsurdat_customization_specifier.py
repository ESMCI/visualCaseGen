import pytest

from visualCaseGen.custom_widget_types.fsurdat_area_specifier import FsurdatAreaSpecifier

def test_fsurdat_area_specifier():
    w = FsurdatAreaSpecifier()

    # initially child widgets are not shown:
    assert w._south.layout.display == "none"
    assert w._north.layout.display == "none"
    assert w._west.layout.display == "none"
    assert w._east.layout.display == "none"
    assert w._land_mask_file_path.layout.display == "none"

    # set mode to "Via corner coordinates"
    w._mode_selector.value = "Via corner coordinates"
    # acquire and release the lock to simulate a frontend change
    w._mode_selector._property_lock = {"value": w._mode_selector.value}
    w._mode_selector._property_lock = {}

    # now coordinate widgets are shown:
    assert w._south.layout.display == ""
    assert w._north.layout.display == ""
    assert w._west.layout.display == ""
    assert w._east.layout.display == ""
    assert w._land_mask_file_path.layout.display == "none"

    # check the value
    assert w.value.startswith("coords:")

    # frontend changes the value
    w._east.value = 50
    assert w.value.endswith(",50.0")

    # backend changes the value
    w.value = "coords:10,90,0,180"
    assert w._south.value == 10

    # switch to "Via mask file"
    w._mode_selector.value = "Via mask file"
    # acquire and release the lock to simulate a frontend change
    w._mode_selector._property_lock = {"value": w._mode_selector.value}
    w._mode_selector._property_lock = {}


    assert w._land_mask_file_path.layout.display == ""
    assert w._south.layout.display == "none"
    assert w._north.layout.display == "none"
    assert w._west.layout.display == "none"
    assert w._east.layout.display == "none"


    #switch again
    w._mode_selector.value = "Via corner coordinates"
    w._mode_selector._property_lock = {"value": w._mode_selector.value}
    w._mode_selector._property_lock = {}

    w._mode_selector.value = "Via mask file"
    w._mode_selector._property_lock = {"value": w._mode_selector.value}
    w._mode_selector._property_lock = {}
    assert w._mode_selector.value == "Via mask file"

    # check the value
    assert w.value == None
