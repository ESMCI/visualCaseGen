from hypothesis.strategies import integers
from hypothesis import given
from visualCaseGen.custom_widget_types.case_creator import CaseCreator

@given(integers(min_value=1, max_value=1e8))
def test_calc_cores_based_on_grid_all_values(num_points):
    """Test that the number of cores is calculated correctly based on the grid."""
    assert CaseCreator._calc_cores_based_on_grid(num_points)


def test_calc_cores_based_on_grid_cases():
    assert CaseCreator._calc_cores_based_on_grid(1) == 16

    assert CaseCreator._calc_cores_based_on_grid(32) == 16

    assert CaseCreator._calc_cores_based_on_grid(801*128) == 144

    assert CaseCreator._calc_cores_based_on_grid(128*32 -1 ) == 112
    