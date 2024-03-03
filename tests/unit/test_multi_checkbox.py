import pytest

from visualCaseGen.custom_widget_types.multi_checkbox import MultiCheckbox

def test_catch_len_mismatch():
    """Test that MultiCheckbox raises an AssertionError if the length of the options and tooltips lists are not equal."""
    with pytest.raises(AssertionError):
        MultiCheckbox(
            options=("a", "b", "c"),
            tooltips=("A", "B", "C", "D")
        )

def test_check_value_assignment():
    """Test that MultiCheckbox.value can only be assigned a tuple of strings that are in MultiCheckbox.options."""
    mc = MultiCheckbox(
        options=("a", "b", "c"),
        tooltips=("a", "b", "c")
    )

    mc.value = "a",
    assert mc.value == ("a",)

    with pytest.raises(ValueError):
        mc.value = ("d",)

    # Test that the value is unchanged after an invalid assignment.
    assert mc.value == ("a",)

def test_filter_options():
    """Test that MultiCheckbox.options can be filtered by a string."""

    # Test initialization with options and tooltips
    mc = MultiCheckbox(
        options=("a", "b", "c"),
        tooltips=("A", "B", "C")
    )
    aux_test_filter(mc)

    # Test initialization to empty options and tooltips and reassignment
    mc = MultiCheckbox()
    mc.options = ("a", "b", "c")
    mc.tooltips = ("A", "B", "C")
    aux_test_filter(mc)

    # Test reassignment of options and tooltips
    mc = MultiCheckbox(
        options=("foo", "bar", "baz"),
        tooltips=("Foo", "Bar", "Baz")
    )
    mc.options = ("a", "b", "c")
    mc.tooltips = ("A", "B", "C")
    aux_test_filter(mc)

def aux_test_filter(mc):
    """Check initial state of MultiCheckbox object and test filtering."""

    # Test if the options and tooltips are assigned correctly
    assert mc.options == ("a", "b", "c")
    assert mc._tooltips == ("A", "B", "C")

    # Test exact match
    mc._filter_textbox.value = '"b"'
    assert mc._filtered_options == ("b",)
    assert mc._filtered_tooltips == ("B",)
    assert mc._len_options_to_display() == 1

    # Test non-exact match
    mc._filter_textbox.value = "b c"
    assert mc._filtered_options == ("b","c")
    assert mc._filtered_tooltips == ("B","C")
    assert mc._len_options_to_display() == 2

    ## Test no match
    mc._filter_textbox.value = '"b c"'
    assert mc._filtered_options == ()
    assert mc._filtered_tooltips == ()
    assert mc._len_options_to_display() == 0

def test_options_reassigment():
    """Test that MultiCheckbox.options can be reassigned."""
    mc = MultiCheckbox(
        options=("a", "b", "c"),
        tooltips=("A", "B", "C")
    )

    mc.options = ("d", "e", "f")
    assert mc._filtered_options == ("d", "e", "f")
    assert mc._filtered_tooltips == ('', '', '') 
    assert mc._len_options_to_display() == 3

    mc.options = ("g", "h", "i", "j")
    mc.tooltips = ("G", "H", "I", "J")
    assert mc._filtered_options == ("g", "h", "i", "j")
    assert mc._filtered_tooltips == ("G", "H", "I", "J")
    assert mc._len_options_to_display() == 4
