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
        title="1. Component Set",
        description="The first step of creating a CESM experiment is to choose a compset, i.e., "
        "a component set. The first choice is between a standard compset and a custom compset. "
        "If you choose to pick a standard compset, you will be prompted to select from a list "
        "of compsets already defined within CESM. If you choose to build a custom compset, "
        "you will be prompted to mix and match individual models and their options.",
        widget=StageWidget(VBox),
        varlist=[cvars["COMPSET_MODE"]],
    )

    # Standard Component Set Stages

    stg_standard_compset = Stage(
        title="Standard Component Set",
        description="",
        parent=stg_compset,
        activation_guard=cvars["COMPSET_MODE"] == "Standard",
    )

    stg_support_level = Stage(
        title="Support Level",
        description="When selecting a standard compset, you have the option to choose from "
        "all standard compsets or only those that are scientifically supported, i.e., "
        "validated by the CESM developers. The former options is useful for testing and "
        "development. The latter option is recommended for production runs.",
        widget=StageWidget(VBox),
        parent=stg_standard_compset,
        varlist=[cvars["SUPPORT_LEVEL"]],
    )

    stg_support_level_all = Stage(
        title="All standard compsets",
        description="",
        parent=stg_support_level,
        activation_guard=cvars["SUPPORT_LEVEL"] == "All",
    )

    stg_comp_filter = Stage(
        title="Models to Include",
        description="Before choosing a compset, you have the option to apply filters to "
        "the list of compsets by indicating the models you are interested in. This is "
        "useful when you are only interested in compsets that include a specific model or set of "
        "models. If you are interested in all compsets, you can click *any* buttons for all "
        "component classes. ",
        widget=StageWidget(HBox),
        parent=stg_support_level_all,
        varlist=[
            cvars[f"COMP_{comp_class}_FILTER"] for comp_class in cime.comp_classes
        ],
        auto_set_default_value=False, # Let the user set defaults via Stage widget button.
    )

    str_comp_alias_all = Stage(
        title="Standard Compsets",
        description="Please select from the below list of compsets, where each compset is "
        "denoted by an alias followed by the initialization time and brief descriptions of "
        "the models included. You can type keywords in the search box to narrow down the list. "
        "For exact matches, you can use double quotes. Otherwise, the search will display all "
        "compsets containing one or more of the words in the search box.",
        widget=StageWidget(VBox),
        parent=stg_support_level_all,
        varlist=[
            cvars["COMPSET_ALIAS"],
        ],
        #todo aux_varlist= [
        #todo     cvars[f"COMP_{comp_class}_PHYS"] for comp_class in cime.comp_classes
        #todo ]+[cvars["COMPSET_LNAME"]],
        # uncommenting above lines currently result in Variable precedence conflict because these variables are
        # also designated as aux_varlist in stg_comp_option. However, there should not be any precedence conflict
        # because standard compset and custom compset tracks are not overlapping. When checking for precedence
        # conflicts, the code should check for precedence conflicts for each branch of the stage tree seperately.
    )

    stg_support_level_sci = Stage(
        title="Scentifically supported compsets",
        description="",
        parent=stg_support_level,
        activation_guard=cvars["SUPPORT_LEVEL"] == "Supported",
    )

    stg_scientific_compset_aliases = Stage(
        title="Supported compsets",
        description="Please select from the below list of compsets, where each compset is "
        "denoted by an alias followed by the initialization time and brief descriptions of "
        "the models included. You can type keywords in the search box to narrow down the list. "
        "For exact matches, you can use double quotes. Otherwise, the search will display all "
        "compsets containing one or more of the words in the search box.",
        widget=StageWidget(VBox),
        parent=stg_support_level_sci,
        varlist=[
            cvars["COMPSET_ALIAS"],
        ],
    )

    # Custom Component Set Stages

    stg_custom_compset = Stage(
        title="Custom Component Set",
        description="",
        parent=stg_compset,
        activation_guard=cvars["COMPSET_MODE"] == "Custom",
    )

    stg_inittime = Stage(
        title="Model Time Period:",
        description="Select the initialization time for the experiment. This "
        "influences the initial conditions and forcings used in the simulation. 1850 "
        "corresponds to pre-industrial conditions and is appropriate for fixed-time-period "
        "runs, e.g., for spinning up the model. 2000 is similarly appropriate for "
        "fixed-time-period runs, but with present-day conditions. HIST is appropriate for "
        "transient runs, e.g., for simulations from 1850 through 2015.",
        widget=StageWidget(VBox),
        parent=stg_custom_compset,
        varlist=[cvars["INITTIME"]],
    )

    stg_comp = Stage(
        title="Components",
        description="To build a custom component set, select models from each component class. "
        "Models beginning with the letter d (e.g., datm) are data models. Models beginning with "
        "the letter s, (e.g., sice) are stub models (placeholders that have no impact). Others "
        "are fully active models.",
        widget=StageWidget(HBox),
        parent=stg_custom_compset,
        varlist=[cvars[f"CUSTOM_{comp_class}"] for comp_class in cime.comp_classes],
    )

    stg_comp_phys = Stage(
        title="Component Physics",
        description="For each component, select the physics configuration. The physics "
        "configuration determines the complexity of the model and the computational cost. "
        "Refer to individual model documentations for more information.",
        widget=StageWidget(HBox),
        parent=stg_custom_compset,
        varlist=[cvars[f"CUSTOM_{comp_class}_PHYS"] for comp_class in cime.comp_classes],
    )

    stg_comp_option = Stage(
        title="Component Options",
        description="Component options, which are also known as modifiers, allow users to "
        "apply further customizations to the model physics. Switch between the tabs to "
        "select options for each component. The question marks next to the tab titles indicate "
        "the components for which no options have been selected yet. You have the option to "
        "apply more than one modifier by switching to multi selection mode, but be aware that "
        "visualCaseGen does not check for compatibility between multiple modifiers.",
        widget=StageWidget(Tab),
        parent=stg_custom_compset,
        varlist=[
            cvars[f"CUSTOM_{comp_class}_OPTION"] for comp_class in cime.comp_classes
        ],
        aux_varlist= [
            cvars[f"COMP_{comp_class}_PHYS"] for comp_class in cime.comp_classes
        ]+[cvars["COMPSET_LNAME"]],
    )

    comp_class_ix = {comp_class: i for i, comp_class in enumerate(cime.comp_classes)}

    def refresh_comp_options_tab_title(change):
        """Refresh the title of the component options tab when the value changes:
        If a value is set, display a checkmark; otherwise, display a question mark."""
        comp_class = change["owner"].name.split("_")[1]
        new_title = f"{comp_class} {chr(int('2714', base=16)) if change['new'] else chr(int('2753', base=16))}"
        stg_comp_option._widget._main_body.set_title(
            comp_class_ix[comp_class], new_title
        )

    # Explicitly call refresh_comp_options_tab_title to initialize the tab titles
    # and set up the observers for the component options to update the tab titles.
    for comp_class in cime.comp_classes:
        refresh_comp_options_tab_title(
            {
                "owner": cvars[f"CUSTOM_{comp_class}_OPTION"],
                "new": cvars[f"CUSTOM_{comp_class}_OPTION"].value,
            }
        )
        cv_comp_option = cvars[f"CUSTOM_{comp_class}_OPTION"]
        cv_comp_option.observe(
            refresh_comp_options_tab_title, names="value", type="change"
        )
