import ipywidgets as widgets
from traitlets import Int, Any, observe
from ipywidgets import trait_types
from ProConPy.out_handler import handler as owh
from ProConPy.dialog import alert_warning

_checkbox_width = "185px"
_checkbox_clm_width = "200px"
_min_widget_width = "720px"

# The number of options that are displayed when the display mode is set to "less".
less_options_threshold = 20


class CheckboxMultiWidget(widgets.VBox, widgets.ValueWidget):
    """A widget that allows the user to select multiple options from a list of options. The options are displayed as
    checkboxes. The user can select multiple options if the allow_multi_select flag is set to True. If the flag is set
    to False, only a single option may be selected. The user can switch between single and multiple selection modes
    using the selection mode button. The display mode button allows the user to switch between a compact and a detailed
    view of the options. The detailed view is useful when the number of options is large. The user can also see tooltips
    which are displayed next to the options. The tooltips are useful when the options are not self-explanatory.
    """

    value = trait_types.TypedTuple(trait=Any(), help="Selected values").tag(sync=True)
    options = Any(
        (),
        help="Iterable of values, (label, value) pairs, or a mapping of {label: value} pairs that the "
        "user can select.",
    )

    def __init__(
        self,
        value=None,
        options=None,
        description="",
        disabled=False,
        allow_multi_select=True,
        display_mode="less",  # "less" or "all" or None
    ):
        """Construct a CheckboxMultiWidget.

        Parameters
        ----------
        value : tuple, optional
            The initial value of the widget. The default is None.
        options : tuple, optional
            The options that the user can select. The default is None.
        description : str, optional
            The description of the widget. The default is "".
        disabled : bool, optional
            If True, the widget is disabled. The default is False.
        allow_multi_select : bool, optional
            If True, the user may select multiple options. If False, only a single option may be selected. The default
            is True.
        display_mode : str, optional
            The display mode of the options. If "less", only a few options are displayed. If "all", all options are
            displayed. The default is "less". If None, all options are displayed and the display mode button is not
            shown.
        """

        super().__init__()

        # Arguments
        self._options = ()
        self.description = description  # currently not displayed.
        self._disabled = disabled
        self._allow_multi_select = allow_multi_select  # if false, only a single options may be selected on the frontend.
        self._select_multiple = (
            False  # if true, multiple options may be selected on the frontend.
        )
        assert display_mode in ["less", "all", None], "Invalid display mode."
        self._display_mode = display_mode

        # Properties
        self._options_indices = {}  # keys: option names, values: option indexes
        self._options_widgets = ()  # a (subset of) list of options that are currently displayed
        self._tooltips = []  # tooltips for the options
        self._len_options_widgets = (
            0  # the number of options that are currently displayed
        )

        # Widgets
        # (1) selection mode button
        # (2) options: (2.a) checkboxes, (2.b) tooltips
        # (3) display mode button
        self._init_select_mode_btn()
        self._init_options_tooltips_hbox()
        self._init_display_mode_btn()

        # Set all main children
        children_list = []
        if self._allow_multi_select:
            children_list.append(self._select_mode_btn)
        children_list.append(self._options_tooltips_hbox)
        if display_mode is not None:
            children_list.append(self._display_mode_btn)
        self.children = children_list

        # update disabled flags of all elements
        self._propagate_disabled_flag()

        if options:
            self.set_trait("options", options)
        if value:
            self.set_trait("value", value)

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, disabled):
        if self._disabled != disabled:
            self._disabled = disabled
            self._propagate_disabled_flag()

    @property
    def index(self):
        raise NotImplementedError("The index trait is not implemented.")

    def _propagate_disabled_flag(self):
        """Propagate the disabled flag to all children."""
        self._select_mode_btn.disabled = self._disabled
        self._display_mode_btn.disabled = self._disabled
        for cbox in self._options_widgets:
            cbox.disabled = self._disabled

    def _init_select_mode_btn(self):
        """Initialize the selection mode button. The user may switch between single and multiple selection modes."""
        self._select_mode_btn = widgets.ToggleButtons(
            options=["single", "multi"],
            description="Selection:",
            tooltips=[
                "The user is allowed to pick only one option.",
                "The user may select multiple options. Options compatibility NOT ensured.",
            ],
            layout={"display": "flex", "align_self": "flex-end", "margin": "5px"},
        )
        self._select_mode_btn.style.button_width = "60px"
        self._select_mode_btn.style.height = "30px"

        @owh.out.capture()
        def on_select_mode_change(change):
            new_val = change["new"]
            if new_val == "single":
                self._select_multiple = False
                if len(self.value) > 1:
                    self._set_value(())
            else:
                warn_msg = (
                    """visualCaseGen doesn't check the compatibility of multiple options. """
                    """Use this mode with caution! Refer to the component documentation to check which options """
                    """may be combined."""
                )
                alert_warning(warn_msg)
                self._select_multiple = True

        self._select_mode_btn.observe(
            on_select_mode_change, names="value", type="change"
        )

    def _init_options_tooltips_hbox(self):
        """Initialize the options hbox. The options are displayed as checkboxes with descriptive tooltips."""

        self._options_vbox = widgets.VBox(
            layout={
                "max_width": _checkbox_clm_width,
                "min_width": _checkbox_clm_width,
                "overflow": "hidden",
                },
        )

        self._tooltips_widget = widgets.HTML(value="", placeholder="", description="")

        self._options_tooltips_hbox = widgets.HBox(
            children=[self._options_vbox, self._tooltips_widget],
            layout={
                "display": "flex",
                "min_width": _min_widget_width,
                "width": "max-content",
                "justify_content": "flex-start",
            }
        )

    def _switch_display_mode(self, b=None):
        """Switch between a compact and a detailed view of the options.

        Parameters
        ----------
        b : widget, optional
            The widget that triggered the event. The default is None.
        """

        if self._display_mode == "all":
            self._display_mode = "less"
        else:
            self._display_mode = "all"

        self._display_mode_btn.icon = "hourglass-start"
        self._display_mode_btn.description = "Loading..."

        # reset the value
        old_value = self.value
        self._set_value(())

        # update the widgets
        self._gen_options_widgets(
            reuse_widgets=False, status_change_only=False, display_mode_change_only=True
        )

        # recover the old value if it's still displayed
        if all(opt in self._options[: self._len_options_widgets] for opt in old_value):
            self._set_value(old_value)

        if self._display_mode == "all":
            self._display_mode_btn.icon = "chevron-up"
            self._display_mode_btn.description = "Show Less"
        else:
            self._display_mode_btn.icon = "chevron-down"
            self._display_mode_btn.description = "Show All"

    def _init_display_mode_btn(self):
        """Initialize the display mode button. The user may switch between a compact and a detailed view of the options."""
        self._display_mode_btn = widgets.Button(
            description="Show All",
            icon="chevron-down",
            layout={"align_self": "center", "margin": "5px"},
        )
        self._display_mode_btn.on_click(self._switch_display_mode)

    def _set_value(self, new_value):
        """Programmatically set the value of the widget and acquire and release the property
        lock to ensure that the change propagates to the backend."""
        self.value = new_value
        self._property_lock = {"value": self.value}
        self._property_lock = {}

    def update_value(self, change):
        """changes propagate from frontend (js checkboxes) to the backend (CheckboxMultiWidget class)"""

        opt = change["owner"].description
        new_val = change["new"]
        if new_val is True:
            if opt not in self.value:
                if self._select_multiple:
                    self.value += (opt,)
                else:
                    self.value = (opt,)
                # let the observers know that a frontend-invoked change was made:
                self._property_lock = {"value": self.value}
        else:
            if opt in self.value:
                if self._select_multiple:
                    val_list = list(self.value)
                    val_list.remove(opt)
                    self.value = tuple(val_list)
                else:
                    self.value = ()
                # let the observers know that a frontend-invoked change was made:
                self._property_lock = {"value": self.value}

        self._property_lock = {}

    @observe("options")
    def _set_options(self, change):
        """When options trait changes, update the internal _options and _options_indices attributes.
        Also, update the frontend checkboxes and tooltips."""

        new_opts = change["new"]
        self.value = ()
        assert isinstance(new_opts, tuple)

        # check if the number of options is the same as before. If so, reuse the
        # existing widgets. This improves the performance a lot. (e.g., when
        # changes occur only in the options name such as a status update)
        reuse_widgets = False
        status_change_only = False
        if len(self._options) == len(new_opts):
            reuse_widgets = True
            status_change_only = [opt[1:] for opt in self._options] == [
                opt[1:] for opt in new_opts
            ]

        # update options
        self._options = tuple(new_opts)
        self._options_indices = {new_opts[i]: i for i in range(len(new_opts))}

        # if there aren't enough options, do not show selection mode button
        if len(new_opts) < 2:
            self._select_mode_btn.layout.display = "none"
        else:
            self._select_mode_btn.layout.display = ""

        # if there aren't enough options, do not show display mode button
        if len(new_opts) <= less_options_threshold:
            self._display_mode_btn.layout.display = "none"
        else:
            self._display_mode_btn.layout.display = ""

        # update widgets
        self._gen_options_widgets(reuse_widgets, status_change_only)

    def _gen_options_widgets(
        self, reuse_widgets, status_change_only, display_mode_change_only=False
    ):
        """Generate the options checkboxes and tooltips. If reuse_widgets is True, the existing widgets are reused.

        Parameters
        ----------
        reuse_widgets : bool
            If True, the existing widgets are reused. If False, new widgets are created.
        status_change_only : bool
            If True, only the status of the options has changed. If False, the options have changed.
        """

        self._len_options_widgets = len(self._options)
        if self._display_mode == "less":
            self._len_options_widgets = min(
                less_options_threshold, self._len_options_widgets
            )

        for opt_widget in self._options_widgets:
            opt_widget.unobserve(self.update_value, names="value", type="change")

        if reuse_widgets:
            for opt_ix, opt in enumerate(self._options[: self._len_options_widgets]):
                self._options_widgets[opt_ix].description = opt
                self._options_widgets[opt_ix].value = False
            if not status_change_only or not display_mode_change_only:
                self._tooltips = [""] * len(self._options)
        else:
            self._options_widgets = [
                widgets.Checkbox(
                    description=opt,
                    value=False,
                    indent=False,
                    layout=widgets.Layout(
                        max_width=_checkbox_width, left="5px", margin="0px"
                    ),
                )
                for opt in self._options[: self._len_options_widgets]
            ]
            if not display_mode_change_only:
                self._tooltips = [""] * len(self._options)

        for opt_widget in self._options_widgets:
            opt_widget.observe(self.update_value, names="value", type="change")

        if not reuse_widgets:
            self._refresh_options_tooltips()

    @observe("value")
    def _propagate_value(self, change):
        """changes propagate from the backend (CheckboxMultiWidget) to children (i.e., actual checkboxes)"""
        new_vals = change["new"]

        # check if the new vars are displayed by the frontend
        if self._display_mode == "less":
            all_new_vars_shown = all(
                self._options_indices[val] < self._len_options_widgets
                for val in new_vals
            )
            if not all_new_vars_shown:
                self._switch_display_mode()  # switch to "all" mode

        # update checkboxes
        for i, opt in enumerate(self._options[: self._len_options_widgets]):
            opt_widget = self._options_widgets[i]

            if opt in new_vals:
                if opt_widget.value is not True:
                    opt_widget.value = True
            else:
                if opt_widget.value is not False:
                    opt_widget.value = False

    def _refresh_tooltips(self):
        """Refresh the tooltips widget."""
        if self._tooltips is None:
            self._tooltips_widget.value = ""
            return

        self._tooltips_widget.value = ''.join(
            tooltip + "<br>" for tooltip in self._tooltips[: self._len_options_widgets]
        )

    def _refresh_options_tooltips(self):
        """Refresh the options hbox including the checkboxes and tooltips."""
        self._options_vbox.children = self._options_widgets
        self._refresh_tooltips()


    @property
    def tooltips(self):
        return self._tooltips

    @tooltips.setter
    def tooltips(self, new_tooltips):
        assert len(new_tooltips) == len(
            self._options
        ), "Tooltips length is not equal to options length."
        self._tooltips = new_tooltips
        self._refresh_tooltips()
