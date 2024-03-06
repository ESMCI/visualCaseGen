import re
import ipywidgets as widgets
from traitlets import Any, observe, validate
from ipywidgets import trait_types
from ProConPy.out_handler import handler as owh
from ProConPy.dialog import alert_warning

_checkbox_width = "190px"
_less_options = 10


class MultiCheckbox(widgets.VBox, widgets.ValueWidget):
    """A multi-checkbox widget. The user may select multiple options from a list of options.
    The options are displayed as checkboxes. The user may filter the options by typing in a textbox.
    The user may also switch between displaying all options and displaying only a few options.
    """

    value = trait_types.TypedTuple(trait=Any(), help="Selected values").tag(sync=True)
    options = Any((), help="Options to display.").tag(sync=True)

    def __init__(
        self,
        value=(),
        options=(),
        tooltips=(),
        description="",
        disabled=False,
        allow_multi_select=False,
        display_mode="less",
        filter=True,
        placeholder="The options list is empty. Try removing the filter (if any).",
    ):
        """Create a new MultiCheckbox widget.

        Parameters
        ----------
        value : tuple, optional
            The initial value of the widget. The default is ().
        options : tuple, optional
            The options to display. The default is ().
        tooltips : tuple, optional
            The tooltips to display next to the options. The default is ().
        description : str, optional
            The description of the widget. The default is "".
        disabled : bool, optional
            Whether the widget is disabled. The default is False.
        allow_multi_select : bool, optional
            Whether the user is allowed to select multiple options. The default is False.
        display_mode : str, optional
            The initial display mode. The default is "less".
        filter : bool, optional
            Whether the user is allowed to filter the options. The default is True.
        placeholder : str, optional
            The text to display when the options are empty. The default is "".
        """

        super().__init__()

        assert isinstance(value, tuple), "value must be a tuple"
        assert isinstance(options, tuple), "options must be a tuple"
        assert isinstance(tooltips, (list, tuple)), "tooltips must be a list or tuple"
        assert len(tooltips) == 0 or len(tooltips) == len(
            options
        ), "tooltips must be the same length as options"
        assert display_mode in ["less", "all"], "display_mode must be 'less' or 'all'"

        # Arguments
        self._description = description
        self._disabled = disabled
        self._allow_multi_select = allow_multi_select
        self._multi_select = False
        self._display_less = display_mode == "less"
        self._filter = filter

        # Auxiliary widgets
        self._mode_selection_btn = self._gen_mode_selection_btn()
        self._filter_textbox = self._gen_filter_textbox()
        self._placeholder_label = widgets.Label(
            value=placeholder,
            layout={
                "display": "none",
                "margin": "5px",
                "align_self": "center",
            },
        )
        self._display_mode_btn = self._gen_display_mode_btn()

        # Options and tooltips widgets
        self._options_vbox = widgets.VBox(
            layout={"overflow": "hidden", "max_width": "200px", "min_width": "200px"},
        )
        self._tooltips_widget = widgets.HTML()

        # Options and tooltips
        # (Filtered options and tooltips correspond to the options and tooltips that are obtained
        # after filtering the full options and tooltips. If the number of filtered options is
        # still too large, a subset may be shown depending on the display mode: less or all.)
        self._filtered_options = options
        self.set_trait("options", options)
        self._tooltips = tooltips
        self._filtered_tooltips = self._tooltips

        self._refresh_options_widgets()
        self._refresh_tooltips()

        # Set children to widgets
        self.children = [
            self._mode_selection_btn,
            self._filter_textbox,
            widgets.HBox(
                [self._options_vbox, self._tooltips_widget],
                layout={
                    "display": "flex",
                    "min_width": "720px",
                    "width": "max-content",
                    "justify_content": "flex-start",
                },
            ),
            self._placeholder_label,
            self._display_mode_btn,
        ]

        # Having generated all the widgets, we can now set the disabled flags
        self._propagate_disabled_flag()

        if value:
            self.set_trait("value", value)

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        """Set the disabled flag of the widget and propagate it to the children."""
        if self._disabled != value:
            self._disabled = value
            self._propagate_disabled_flag()

        # if set to be disabled and value is empty, reset display mode to less
        if value and self.value == () and not self._display_less:
            self._switch_display_mode()

    def _propagate_disabled_flag(self):
        """Propagate the disabled flag to all the children."""
        self._mode_selection_btn.disabled = self._disabled
        self._filter_textbox.disabled = self._disabled
        self._display_mode_btn.disabled = self._disabled
        for checkbox in self._options_vbox.children:
            checkbox.disabled = self._disabled

    def _gen_mode_selection_btn(self):
        """Generate and return a mode selection button instance. This button allows the user to
        switch between single and multi selection.

        Returns
        -------
        widgets.ToggleButtons
            The mode selection button.
        """

        @owh.out.capture()
        def on_mode_selection_change(change):
            """Callback for the mode selection button."""
            new_val = change["new"]
            if new_val == "single":
                self._multi_select = False
                if len(self.value) > 1:
                    self.value = ()
                    self._signal_value_to_backend()
            else:
                warn_msg = (
                    """visualCaseGen doesn't check the compatibility of multiple options. """
                    """Use this mode with caution! Refer to the component documentation to check which options """
                    """may be combined."""
                )
                alert_warning(warn_msg)
                self._multi_select = True

            # End of on_mode_selection_change

        display = "" if self._allow_multi_select is True else "none"
        mode_selection_btn = widgets.ToggleButtons(
            options=["single", "multi"],
            description="Selection:",
            tooltips=[
                "The user is allowed to pick only one option.",
                "The user may select multiple options. Options compatibility NOT guaranteed.",
            ],
            layout={
                "display": display,
                "align_self": "flex-end",
                "margin": "5px",
                "width": "max-content",
            },
            style={"button_width": "max-content", "description_width": "max-content"},
        )
        mode_selection_btn.observe(
            on_mode_selection_change, names="value", type="change"
        )
        return mode_selection_btn

    def _gen_filter_textbox(self):
        """Generate and return a filter textbox instance. This textbox allows the user to filter the
        options by typing in a string.

        Returns
        -------
        widgets.Text
            The filter textbox."""

        def filtered_options_list(filter_text):
            """Return the options that match the filter text. The filter text is split into exact
            keywords and other keywords. The options must contain all exact keywords and at least one
            of the other keywords. Exact keywords are enclosed in double quotes. The options are
            compared case-insensitively."""

            # all keywords
            filter_text_split_quotes = filter_text.split('"')
            exact_keywords = [
                keyword
                for keyword in filter_text_split_quotes[1::2]
                if keyword.strip() != ""
            ]
            other_keywords = [
                keyword
                for keyword in " ".join(filter_text_split_quotes[0::2]).split(" ")
                if keyword.strip() != ""
            ]

            return tuple(
                opt
                for opt in self.options
                if (
                    (
                        opt_text_lower := opt.lower()
                        + self._tooltips[self._options_ix[opt]].lower()
                    )
                    and any([keyword in opt_text_lower for keyword in other_keywords])
                    or not other_keywords
                )
                and (
                    all([keyword in opt_text_lower for keyword in exact_keywords])
                    or not exact_keywords
                )
            )

        def on_filter_textbox_change(change):
            """Callback for the filter textbox."""
            filter_text = change["new"].lower().strip()
            old_value = self.value

            if filter_text == "":
                self._filtered_options = self.options
                self._filtered_tooltips = self._tooltips
            else:
                # reset value
                if old_value != ():
                    self.value = ()
                    self._signal_value_to_backend()

                # filter options must contain all exact keywords and at least one of the other keywords
                self._filtered_options = filtered_options_list(filter_text)

                self._filtered_tooltips = tuple(
                    self._tooltips[self._options_ix[opt]]
                    for opt in self._filtered_options
                )

            self._refresh_options_widgets()
            self._refresh_tooltips()

            # End of on_filter_textbox_change

        filter_textbox = widgets.Text(
            description="Search:",
            layout={
                "display": "flex",
                "align_self": "flex-end",
                "margin": "5px",
                "width": "500px",
            },
        )
        filter_textbox.observe(on_filter_textbox_change, names="value", type="change")
        return filter_textbox

    def _gen_display_mode_btn(self):
        """Generate and return a display mode button instance. This button allows the user to switch
        between displaying all options and displaying only a few options (_less_options).

        Returns
        -------
        widgets.Button
            The display mode button.
        """
        display_mode_btn = widgets.Button(
            description="Show All",
            icon="chevron-down",
            layout={"align_self": "center", "margin": "5px"},
        )
        display_mode_btn.on_click(self._switch_display_mode)
        return display_mode_btn

    def _switch_display_mode(self, b=None):
        """Switch between displaying all options and displaying only a few options (_less_options)."""

        # switch display mode
        self._display_less = not self._display_less

        self._display_mode_btn.icon = "hourglass-start"
        self._display_mode_btn.description = "Loading..."

        # reset value (this is temporary unless the old value is not displayed anymore)
        old_value = self.value
        self.value = ()

        # refresh options and tooltips
        self._refresh_options_widgets()
        self._refresh_tooltips()

        # set to old value if it's still in the options
        if all(
            opt in self._filtered_options[: self._len_options_to_display()]
            for opt in old_value
        ):
            self.value = old_value

        # signal value change to backend
        if self.value != old_value:
            self._signal_value_to_backend()

        self._display_mode_btn.icon = (
            "chevron-down" if self._display_less else "chevron-up"
        )
        self._display_mode_btn.description = (
            "Show All" if self._display_less else "Show Less"
        )

    @validate("value")
    def _validate_value(self, proposal):
        """Validate the value. This method is called whenever the value changes. It ensures that the
        value is a tuple of options and that the options are valid."""

        new_vals = proposal["value"]

        if not isinstance(new_vals, tuple):
            raise ValueError("value must be a tuple")

        if not all(val in self.options for val in new_vals):
            raise ValueError("value must contain only valid options")

        return proposal["value"]

    @observe("value")
    def _propagate_values_to_children(self, change):
        """Propagate the value to the children. This method is called whenever the value changes.
        It updates the checkboxes accordingly."""

        new_vals = change["new"]

        # check if the new vars are all displayed
        if self._display_less or self._filter_textbox.value != "":
            all_new_vals_displayed = all(
                val in self._filtered_options[: self._len_options_to_display()]
                for val in new_vals
            )
            if not all_new_vals_displayed:
                self._filter_textbox.value = ""
                self._switch_display_mode()

        # update checkboxes
        for cb in self._options_vbox.children:
            if cb.description in new_vals:
                if cb.value is False:
                    cb.value = True
            else:
                if cb.value is True:
                    cb.value = False

    def _signal_value_to_backend(self):
        """Signal the value to the backend by acquiring and releasing the property lock.
        This method should be called whenever a value change is ready to be sent to the backend.
        """
        # acquire lock
        self._property_lock = {"value": self.value}
        # release lock
        self._property_lock = {}

    def _len_options_to_display(self):
        """Return the number of options to display. This number is either _less_options or the
        length of the filtered options, depending on the display mode and the number of filtered
        options."""

        return (
            min(len(self._filtered_options), _less_options)
            if self._display_less
            else len(self._filtered_options)
        )

    def _refresh_options_widgets(self):
        """Update the options widget. This method should be called whenever the (filtered) options
        change. It either reuses the existing checkboxes and updates their descriptions, or generates
        new checkboxes. It also updates the display mode button."""

        if (l := self._len_options_to_display()) <= len(self._options_vbox.children):
            # reuse existing widgets and update their descriptions

            # if needed, shrink the list of checkboxes and unobserve the leftover ones
            if l < len(self._options_vbox.children):
                self._options_vbox.children = self._options_vbox.children[:l]
                for stale_cb in self._options_vbox.children[l:]:
                    stale_cb.unobserve(
                        self._on_checkbox_change, names="value", type="change"
                    )

            self._refresh_checkbox_descriptions()

        else:  # need brand new checkboxes

            # unobserve old widgets
            for stale_cb in self._options_vbox.children:
                stale_cb.unobserve(
                    self._on_checkbox_change, names="value", type="change"
                )

            # generate new widgets
            self._options_vbox.children = [
                widgets.Checkbox(
                    description=option,
                    value=False,
                    indent=False,
                    disabled=self._disabled,
                    layout={
                        "max_width": _checkbox_width,
                        "left": "10px",
                        "margin": "0px",
                    },
                )
                for option in self._filtered_options[:l]
            ]

            # observe new widgets
            for cb in self._options_vbox.children:
                cb.observe(self._on_checkbox_change, names="value", type="change")

        # update the display mode button
        if len(self._filtered_options) <= _less_options:
            self._display_mode_btn.layout.display = "none"
        else:
            self._display_mode_btn.layout.display = ""

        # update the placeholder label
        if len(self._filtered_options) == 0:
            self._placeholder_label.layout.display = ""
        else:
            self._placeholder_label.layout.display = "none"

    def _on_checkbox_change(self, change):
        """Callback for the checkboxes. This method is called whenever a checkbox is checked or
        unchecked. It updates the value of the main widget accordingly."""

        opt = change["owner"].description
        new_val = change["new"]

        if new_val is True:
            # a checkbox has been checked
            if opt not in self.value:
                if self._multi_select:
                    self.value += (opt,)
                else:
                    self.value = (opt,)
        else:
            # a checkbox has been unchecked
            if opt in self.value:
                if self._multi_select:
                    self.value = tuple(val for val in self.value if val != opt)
                else:
                    self.value = ()

        self._signal_value_to_backend()

    def _refresh_tooltips(self):
        """Update the tooltips widget. This method should be called whenever the (filtered)
        options or the tooltips change."""
        self._tooltips_widget.value = "<br>".join(
            self._filtered_tooltips[: self._len_options_to_display()]
        )

    @observe("options")
    def _on_options_change(self, change):
        """Callback for the options trait. This method is called whenever the options change. It
        updates the options and tooltips widgets accordingly. It also resets the value of the main
        widget if the old value is not in the new options."""

        new_options = change["new"]
        assert isinstance(new_options, tuple), "options must be a tuple"

        # save old value and reset value
        old_value = self.value
        self.value = ()

        # update options
        self.options = tuple(new_options)
        self._options_ix = {opt: ix for ix, opt in enumerate(new_options)}

        # reset filter
        self._filter_textbox.value = ""
        self._filtered_options = new_options

        # if there aren't enough options, hide the auxiliary widgets
        if len(new_options) < 2:
            self._mode_selection_btn.layout.display = "none"
            self._filter_textbox.layout.display = "none"
        else:
            self._mode_selection_btn.layout.display = (
                "flex" if self._allow_multi_select else "none"
            )
            self._filter_textbox.layout.display = "" if self._filter else "none"

        # if there aren't enough options, hide the display mode button
        if len(new_options) <= _less_options:
            self._display_mode_btn.layout.display = "none"
        else:
            self._display_mode_btn.layout.display = ""

        # update the options and tooltips widgets
        validity_change_only = (
            len(self._filtered_options) == len(self._options_vbox.children)
            and all(len(opt) > 1 for opt in self._filtered_options)
            and all(
                self._filtered_options[ix][1:] == cb.description[1:]
                for ix, cb in enumerate(self._options_vbox.children)
            )
        )

        if validity_change_only:
            # Only the options validities have changed, so we only need to update the validity
            # icons in checkbox descriptions
            self._refresh_checkbox_descriptions()

            # Only the validities have changed, so we can set back to old value
            # (old_value must remain valid when the validities change)
            self.value = old_value
        else:
            # options have changed and new checkboxes are needed
            self._refresh_options_widgets()
            self.tooltips = ["" for _ in new_options]

        if self.value != old_value:
            # value reset, inform backend
            self._signal_value_to_backend()

    def _refresh_checkbox_descriptions(self):
        """Update the descriptions of the checkboxes. This method should be called whenever the
        number of checkboxes remains the same, but the descriptions need to be updated.
        """

        assert len(self._options_vbox.children) == (
            l := self._len_options_to_display()
        ), "The number of checkboxes is not the same as the number of options to display."
        for i in range(l):
            self._options_vbox.children[i].description = self._filtered_options[i]
            self._options_vbox.children[i].value = False

    @property
    def tooltips(self):
        return self._tooltips

    @tooltips.setter
    def tooltips(self, new_tooltips):
        assert isinstance(
            new_tooltips, (list, tuple)
        ), "tooltips must be a list or tuple"
        assert len(new_tooltips) == 0 or len(new_tooltips) == len(
            self.options
        ), "tooltips must be the same length as options"
        self._tooltips = new_tooltips
        self._filtered_tooltips = tuple(
            self._tooltips[self._options_ix[filtered_opt]]
            for filtered_opt in self._filtered_options
        )
        self._refresh_tooltips()
