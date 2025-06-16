import logging
from ipywidgets import VBox, HBox, Button, Output

from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.dialog import alert_error
from visualCaseGen.custom_widget_types.case_creator import CaseCreator, ERROR, RESET

class CaseCreatorWidget(VBox, CaseCreator):
    """A widget for creating a new case and applying initial modifications to it."""

    def __init__(self, cime, **kwargs):
        """Initialize the CaseCreator widget."""

        VBox.__init__(self, **kwargs)
        CaseCreator.__init__(self, cime, Output())

        cvars["CASEROOT"].observe(
            self._on_caseroot_change, names="value", type="change"
        )
        cvars["MACHINE"].observe(self._on_machine_change, names="value", type="change")

        self._btn_create_case = Button(
            description="Create Case",
            layout={"width": "160px", "margin": "5px"},
            button_style="success",
        )
        self._btn_create_case.on_click(self._on_create_case_clicked)

        self._btn_show_commands = Button(
            description="Show Commands",
            layout={"width": "160px", "margin": "5px"},
        )
        self._btn_show_commands.on_click(self._on_create_case_clicked)

        self.children = [
            cvars["PROJECT"].widget,
            HBox(
                [self._btn_create_case, self._btn_show_commands],
                layout={"display": "flex", "justify_content": "center"},
            ),
            self._out,
        ]

    @property
    def disabled(self):
        return super().disabled

    @disabled.setter
    def disabled(self, value):
        # disable/enable all children
        self._btn_create_case.disabled = value
        self._btn_show_commands.disabled = value
        cvars["PROJECT"].widget.disabled = value
        if cvars["CASE_CREATOR_STATUS"].value != "OK":
            # clear only if the case creator wasn't completed
            self._out.clear_output()

    def _on_caseroot_change(self, change):
        """This function is called when the caseroot changes. It resets the output widget."""
        self._out.clear_output()

    def _on_machine_change(self, change):
        """This function is called when the machine changes. It resets the output widget.
        It also shows/hides the project ID text box based on whether the machine requires
        a project ID."""
        new_machine = change["new"]
        cvars["PROJECT"].value = ""
        project_required = self._cime.project_required.get(new_machine, False)
        if project_required:
            cvars["PROJECT"].widget.layout.display = "flex"
        else:
            cvars["PROJECT"].widget.layout.display = "none"
        self._out.clear_output()

    def _on_create_case_clicked(self, b=None):
        """The main function that creates the case and applies initial modifications to it.
        This function is called when the "Create Case" button or the "Show Commands" button
        is clicked.
        
        Parameters
        ----------
        b : Button
            The button that was clicked.
        """
        
        # Determine if the commands should be executed or just displayed
        do_exec = b is not self._btn_show_commands

        # Create the case. If an error occurs, display it in the output widget
        # and revert the launch.
        try:
            self.create_case(do_exec)
        except Exception as e:
            with owh.out:
                alert_error(str(e))
            with self._out:
                print(f"{ERROR}{str(e)}{RESET}")
            self.revert_launch(do_exec)
