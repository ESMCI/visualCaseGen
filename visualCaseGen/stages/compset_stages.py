import logging
from ipywidgets import VBox, HBox, Tab

from ProConPy.config_var import cvars
from ProConPy.stage import Stage, Guard
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

    stg_support_level = Stage(
        title="Support Level",
        description="When selecting a standard compset, you have the option to choose from "
        "all standard compsets or only those that are scientifically supported, i.e., "
        "validated by the CESM developers. The former options is useful for testing and "
        "development. The latter option is recommended for production runs.",
        widget=StageWidget(VBox),
        parent=Guard(
            title= "Standard",
            parent=stg_compset,
            condition=cvars["COMPSET_MODE"] == "Standard",
        ),
        varlist=[cvars["SUPPORT_LEVEL"]],
    )

    guard_support_level_all = Guard(
        title="All",
        parent=stg_support_level,
        condition=cvars["SUPPORT_LEVEL"] == "All",
    )

    stg_comp_filter = Stage(
        title="Models to Include",
        description="Before choosing a compset, you have the option to apply filters to "
        "the list of compsets by indicating the models you are interested in. This is "
        "useful when you are only interested in compsets that include a specific model or set of "
        "models. If you are interested in all compsets, you can click *any* buttons for all "
        "component classes. ",
        widget=StageWidget(HBox),
        parent=guard_support_level_all,
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
        parent=guard_support_level_all,
        varlist=[
            cvars["COMPSET_ALIAS"],
        ],
        aux_varlist=
            [cvars[f"COMP_{comp_class}"] for comp_class in cime.comp_classes]+
            [cvars[f"COMP_{comp_class}_PHYS"] for comp_class in cime.comp_classes]+
            [cvars[f"COMP_{comp_class}_OPTION"] for comp_class in cime.comp_classes]+
            [cvars["COMPSET_LNAME"]]
    )

    stg_scientific_compset_aliases = Stage(
        title="Supported compsets",
        description="Please select from the below list of compsets, where each compset is "
        "denoted by an alias followed by the initialization time and brief descriptions of "
        "the models included. You can type keywords in the search box to narrow down the list. "
        "For exact matches, you can use double quotes. Otherwise, the search will display all "
        "compsets containing one or more of the words in the search box.",
        widget=StageWidget(VBox),
        parent=Guard(
            title="Supported",
            parent=stg_support_level,
            condition=cvars["SUPPORT_LEVEL"] == "Supported",
        ),
        varlist=[
            cvars["COMPSET_ALIAS"],
        ],
        aux_varlist=
            [cvars[f"COMP_{comp_class}"] for comp_class in cime.comp_classes]+
            [cvars[f"COMP_{comp_class}_PHYS"] for comp_class in cime.comp_classes]+
            [cvars[f"COMP_{comp_class}_OPTION"] for comp_class in cime.comp_classes]+
            [cvars["COMPSET_LNAME"]]
    )

    # Custom Component Set Stages

    guard_custom_compset = Guard(
        title="Custom",
        parent=stg_compset,
        condition=cvars["COMPSET_MODE"] == "Custom",
    )

    stg_inittime = Stage(
        title="Time Period",
        description="Select the initialization time for the experiment. This "
        "influences the initial conditions and forcings used in the simulation. 1850 "
        "corresponds to pre-industrial conditions and is appropriate for fixed-time-period "
        "runs, e.g., for spinning up the model. 2000 is similarly appropriate for "
        "fixed-time-period runs, but with present-day conditions. HIST is appropriate for "
        "transient runs, e.g., for simulations from 1850 through 2015.",
        widget=StageWidget(VBox),
        parent=guard_custom_compset,
        varlist=[cvars["INITTIME"]],
    )

    stg_comp = Stage(
        title="Components",
        description="To build a custom component set, select models from each component class. "
        "Models beginning with the letter d (e.g., datm) are data models. Models beginning with "
        "the letter s, (e.g., sice) are stub models (placeholders that have no impact). Others "
        "are fully active models.",
        widget=StageWidget(HBox),
        parent=guard_custom_compset,
        varlist=[cvars[f"COMP_{comp_class}"] for comp_class in cime.comp_classes],
    )

    stg_comp_phys = Stage(
        title="Component Physics",
        description="For each component, select the physics configuration. The physics "
        "configuration determines the complexity of the model and the computational cost. "
        "Refer to individual model documentations for more information.",
        widget=StageWidget(HBox),
        parent=guard_custom_compset,
        varlist=[cvars[f"COMP_{comp_class}_PHYS"] for comp_class in cime.comp_classes],
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
        parent=guard_custom_compset,
        varlist=[
            cvars[f"COMP_{comp_class}_OPTION"] for comp_class in cime.comp_classes
        ],
        aux_varlist= [cvars["COMPSET_LNAME"]],
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
                "owner": cvars[f"COMP_{comp_class}_OPTION"],
                "new": cvars[f"COMP_{comp_class}_OPTION"].value,
            }
        )
        cv_comp_option = cvars[f"COMP_{comp_class}_OPTION"]
        cv_comp_option.observe(
            refresh_comp_options_tab_title, names="value", type="change"
        )
