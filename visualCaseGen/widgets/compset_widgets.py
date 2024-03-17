import logging
import ipywidgets as widgets

from ProConPy.config_var import cvars
from visualCaseGen.custom_widget_types.multi_checkbox import MultiCheckbox

logger = logging.getLogger("\t" + __name__.split(".")[-1])

button_width = "100px"
description_width = "160px"


def initialize_compset_widgets(cime):
    """Construct the compset section of the GUI."""

    cv_compset_mode = cvars["COMPSET_MODE"]
    cv_compset_mode.widget = widgets.ToggleButtons(
        description="Configuration Mode:",
        layout={"display": "flex", "width": "max-content", "padding": "10px"},
        style={"button_width": button_width, "description_width": description_width},
    )

    # Standard Compset Widgets

    cv_support_level = cvars["SUPPORT_LEVEL"]
    cv_support_level.widget = widgets.ToggleButtons(
        description="Include all compsets or scientifically supported only?",
        layout={"display": "flex", "width": "max-content", "padding": "10px"},
        style={"button_width": button_width, "description_width": "max-content"},
    )

    for comp_class in cime.comp_classes:
        cv_comp_filter = cvars[f"COMP_{comp_class}_FILTER"]
        cv_comp_filter.widget = widgets.ToggleButtons(
            description=f'{chr(int("2000",base=16))*5}{chr(int("25BC",base=16))} {comp_class}',
            layout={"width": "120px"},  # , 'max_height':'145px'},
            style={"button_width": "105px", "description_width": "0px"},
        )

    compset_alias = cvars["COMPSET_ALIAS"]
    compset_alias.widget = MultiCheckbox(
        description="Compset Alias: (Scroll horizontally to see all option descriptions.)",
        allow_multi_select=False
    )
    # Custom Compset Widgets

    cv_inittime = cvars["INITTIME"]
    cv_inittime.widget = widgets.ToggleButtons(
        description="Initialization Time:",
        layout={"display": "flex", "width": "max-content", "padding": "10px"},
        style={"button_width": "100px", "description_width": description_width},
    )

    for comp_class in cime.comp_classes:

        cv_comp = cvars[f"CUSTOM_{comp_class}"]
        cv_comp.widget = widgets.ToggleButtons(
            description=f'{chr(int("2000",base=16))*5}{chr(int("25BC",base=16))} {comp_class}',
            layout={"width": "120px"},  # , 'max_height':'145px'},
            style={"button_width": "105px", "description_width": "0px"},
        )

        cv_comp_phys = cvars[f"CUSTOM_{comp_class}_PHYS"]
        cv_comp_phys.widget = widgets.ToggleButtons(
            description=f'{chr(int("2000",base=16))*5}{chr(int("25BC",base=16))} {comp_class}',
            layout={"width": "120px"},  # , 'max_height':'145px'},
            style={"button_width": "105px", "description_width": "90px"},
        )

        cv_comp_option = cvars[f"CUSTOM_{comp_class}_OPTION"]
        cv_comp_option.widget = MultiCheckbox(
            description=comp_class + ":",
            allow_multi_select=True
        )
        cv_comp_option.valid_opt_char = "%"
