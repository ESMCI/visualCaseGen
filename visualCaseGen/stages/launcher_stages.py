import logging
from ipywidgets import VBox, HBox, Button

from ProConPy.config_var import cvars
from ProConPy.stage import Stage
from ProConPy.out_handler import handler as owh
from visualCaseGen.custom_widget_types.stage_widget import StageWidget
from visualCaseGen.custom_widget_types.case_creator_widget import CaseCreatorWidget

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_launcher_stages(cime):
    """Initialize the stages for the case launcher."""

    launcher_vars = [
        cvars["CASEROOT"],
        cvars["MACHINE"],
        cvars["CASE_CREATOR_STATUS"]
    ]
    # Note: PROJECT is not included in the launcher_vars list because it is not always required.

    stg_launch = Stage(
        title="3. Launch",
        description="Create and set up the case by specifying an existing path for its creation "
        "and a unique case name. Additionally, you'll need to choose the machine where the case "
        "will run. If CESM has been ported to the machine, the selection should be automatic. "
        "Otherwise, ensure that CESM is properly ported and the machine selection is accurate. "
        "If the machine requires a PROJECT id, you'll be prompted to provide it. When everything "
        "is set, click either the *Create Case* button or *Show Commands* to view the "
        "corresponding terminal commands.",
        widget=StageWidget(
            VBox,
            supplementary_widgets=[CaseCreatorWidget(cime)]
        ),
        varlist=launcher_vars,
    )