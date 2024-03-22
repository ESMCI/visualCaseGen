import pytest
from traitlets import TraitError

from visualCaseGen.custom_widget_types.fsurdat_matrix import FsurdatMatrix

def test_fsurdat_matrix():
    w = FsurdatMatrix()

    # Test initial value
    assert w.value == 'OK'

    # Test when the new value is not 'OK'
    w.value = 'Not OK'
    assert w.value == 'OK'

    # initial values
    assert w.lai[0].value == 3
    assert w.sai[0].value == 1
    assert w.hgt_top[0].value == 1
    assert w.hgt_bot[0].value == 0.5

    # change lai:
    w.lai[0].value = 5
    assert w.lai[0].value == 5

    # cannot set lai to None:
    with pytest.raises(TraitError):
        w.lai[0].value = None
    assert w.lai[0].value == 5

    # cannot set sai to None:
    with pytest.raises(TraitError):
        w.sai[0].value = None

    # cannot set hgt_top to None:
    with pytest.raises(TraitError):
        w.hgt_top[0].value = None

    # cannot set hgt_bot to None:
    with pytest.raises(TraitError):
        w.hgt_bot[0].value = None

    # value still ok
    assert w.value == 'OK'