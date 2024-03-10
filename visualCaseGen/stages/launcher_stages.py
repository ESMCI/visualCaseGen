import logging
from ipywidgets import VBox, HBox, Button

from ProConPy.config_var import cvars
from ProConPy.stage import Stage
from ProConPy.out_handler import handler as owh
from visualCaseGen.custom_widget_types.stage_widget import StageWidget
from visualCaseGen.utils.create_case import create_case

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_launcher_stages(cime):
    """Initialize the stages for the case launcher."""

    launcher_vars = [
        cvars["CASEROOT"],
        cvars["MACHINE"],
    ]

    # Check if PROJECT id is required for the machine
    project_required = True
    if cime.machine is not None:
        project_required = cime.project_required[cime.machine]

    if project_required:
        launcher_vars.append(cvars["PROJECT"])

    stg_launch = Stage(
        title="3. Launch",
        description="Create and set up the case by specifying an existing path for its creation "
        "and a unique case name. Additionally, you'll need to choose the machine where the case "
        "will run. If CESM has been ported to the machine, the selection should be automatic. "
        "Otherwise, ensure that CESM is properly ported and the machine selection is accurate. "
        "If the machine requires a PROJECT id, you'll be prompted to provide it. When everything "
        "is set, click either the *Create Case* button or *Show Commands* to view the "
        "corresponding terminal commands.",
        widget=StageWidget(VBox),
        varlist=launcher_vars,
    )


    btn_create_case = Button(
        description="Create Case",
        layout={"width": "160px", "margin": "5px"},
    )
    btn_create_case.on_click(lambda b: create_case(b, cime))



    btn_show_commands = Button(
        description="Show Commands",
        layout={"width": "160px", "margin": "5px"},
    )

    stg_launch._widget.children += (
        HBox(
            [btn_create_case, btn_show_commands],
            layout={"display": "flex", "justify_content": "center"},
        ),
    )
