import logging
from ipywidgets import VBox, HBox, Tab

from ProConPy.config_var import cvars
from ProConPy.stage import Stage
from ProConPy.out_handler import handler as owh
from visualCaseGen.custom_widget_types.stage_widget import StageWidget

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_compset_stages(cime):
    """Initialize the stages for compset configuration."""

    stg_compset = Stage(
        title="Step 1: Component Set",
        description="Select the component set and its options",
        widget=StageWidget(VBox),
        varlist=[cvars["COMPSET_MODE"]],
    )

    # Standard Component Set Stages

    stg_standard_compset = Stage(
        title="Standard Component Set",
        description="Select a standard component set from the list",
        parent=stg_compset,
        activation_guard=cvars["COMPSET_MODE"] == "Standard",
    )

    stg_support_level = Stage(
        title="Support Level",
        description="Determine the support level of the compsets: All or Scientific Supported",
        widget=StageWidget(VBox),
        parent=stg_standard_compset,
        varlist=[cvars["SUPPORT_LEVEL"]],
    )

    stg_support_level_all = Stage(
        title="All standard compsets",
        description="Select from the list of all compsets",
        parent=stg_support_level,
        activation_guard=cvars["SUPPORT_LEVEL"] == "All",
    )

    stg_comp_filter = Stage(
        title="Models to Include",
        description="Select the components to display",
        widget=StageWidget(HBox),
        parent=stg_support_level_all,
        varlist=[cvars[f"COMP_{comp_class}_FILTER"] for comp_class in cime.comp_classes],
    )

    str_comp_alias_all = Stage(
        title="Compsets",
        description="Select the compset alias",
        widget=StageWidget(VBox),
        parent=stg_support_level_all,
        varlist=[cvars["COMPSET_ALIAS"],]
    )


    stg_support_level_sci = Stage(
        title="Scentifically supported compsets",
        description="Select from the list of scientifically supported compsets",
        parent=stg_support_level,
        activation_guard=cvars["SUPPORT_LEVEL"] == "Supported",
    )

    stg_scientific_compset_aliases = Stage(
        title="Scientifically supported compsets",
        description="Select the compset alias",
        widget=StageWidget(VBox),
        parent=stg_support_level_sci,
        varlist=[cvars["COMPSET_ALIAS"],]
    )

    # Custom Component Set Stages

    stg_custom_compset = Stage(
        title="Custom Component Set",
        description="Select the custom component set and its options",
        parent=stg_compset,
        activation_guard=cvars["COMPSET_MODE"] == "Custom",
    )

    stg_inittime = Stage(
        title="Model Time Period:",
        description="Select the initialization time",
        widget=StageWidget(VBox),
        parent=stg_custom_compset,
        varlist=[cvars["INITTIME"]],
    )

    stg_comp = Stage(
        title="Components",
        description="Select the components",
        widget=StageWidget(HBox),
        parent=stg_custom_compset,
        varlist=[cvars[f"COMP_{comp_class}"] for comp_class in cime.comp_classes],
    )

    stg_comp_phys = Stage(
        title="Component Physics",
        description="Select the component physics",
        widget=StageWidget(HBox),
        parent=stg_custom_compset,
        varlist=[cvars[f"COMP_{comp_class}_PHYS"] for comp_class in cime.comp_classes],
    )

    stg_comp_option = Stage(
        title="Component Options",
        description="Select the component options",
        widget=StageWidget(Tab),
        parent=stg_custom_compset,
        varlist=[
            cvars[f"COMP_{comp_class}_OPTION"] for comp_class in cime.comp_classes
        ],
    )

    comp_class_ix = {comp_class: i for i, comp_class in enumerate(cime.comp_classes)}

    def refresh_comp_options_tab_title(change):
        """Refresh the title of the component options tab when the value changes:
        If a value is set, display a checkmark; otherwise, display a question mark."""
        comp_class = change['owner'].name.split('_')[1]
        new_title = f"{comp_class} {chr(int('2714', base=16)) if change['new'] else chr(int('2753', base=16))}"
        stg_comp_option._widget._main_body.set_title(comp_class_ix[comp_class], new_title)

    # Explicitly call refresh_comp_options_tab_title to initialize the tab titles
    # and set up the observers for the component options to update the tab titles.
    for comp_class in cime.comp_classes:
        refresh_comp_options_tab_title({
            'owner': cvars[f"COMP_{comp_class}_OPTION"],
            'new': cvars[f"COMP_{comp_class}_OPTION"].value
        })
        cv_comp_option = cvars[f"COMP_{comp_class}_OPTION"]
        cv_comp_option.observe(
            refresh_comp_options_tab_title,
            names='value',
            type='change'
        )


