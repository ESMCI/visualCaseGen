from hypothesis.strategies import integers
from hypothesis import given
from visualCaseGen.custom_widget_types.case_creator import CaseCreator

@given(integers(min_value=1, max_value=1e8))
def test_calc_cores_based_on_grid_all_values(num_points):
    """Test that the number of points doesn't impact the default run of this function"""
    assert CaseCreator._calc_cores_based_on_grid(num_points)


def test_calc_cores_based_on_grid_cases():
    """Test that the number of cores is calculated correctly based on the number of points"""
    # Test minimum possible cores is 1
    assert CaseCreator._calc_cores_based_on_grid(1) == 1

    # Test one under the min pts
    assert CaseCreator._calc_cores_based_on_grid(33) == 1

    # Test ideal cores amount
    assert CaseCreator._calc_cores_based_on_grid(800*128) == 128

    assert CaseCreator._calc_cores_based_on_grid(800*32) == 128

    assert CaseCreator._calc_cores_based_on_grid(740 * 780) == 768


    