import logging
from ipywidgets import ToggleButtons, Text, Dropdown
from ipyfilechooser import FileChooser
from pathlib import Path
from ProConPy.config_var import cvars

from visualCaseGen.custom_widget_types.multi_checkbox import MultiCheckbox
from visualCaseGen.custom_widget_types.disabled_text import DisabledText
from visualCaseGen.custom_widget_types.fsurdat_area_specifier import FsurdatAreaSpecifier
from visualCaseGen.custom_widget_types.fsurdat_matrix import FsurdatMatrix

logger = logging.getLogger("\t" + __name__.split(".")[-1])

description_width = "160px"


def initialize_grid_widgets(cime):
    """Construct the grid widgets for the case configurator."""

    cv_grid_mode = cvars["GRID_MODE"]
    cv_grid_mode.widget = ToggleButtons(
        description="Configuration Mode:",
        layout={"display": "flex", "width": "max-content", "padding": "10px"},
        style={"button_width": "100px", "description_width": description_width},
        disabled=False,
    )

    initialize_standard_grid_widgets(cime)
    initialize_custom_atm_grid_widgets(cime)
    initialize_custom_ocn_grid_widgets(cime)
    initialize_custom_lnd_grid_widgets(cime)

def initialize_standard_grid_widgets(cime):
    # Standard grid options
    cv_grid = cvars["GRID"]
    cv_grid.widget = MultiCheckbox(
        description="Grid:",
        allow_multi_select=False,
    )
    cv_grid.valid_opt_char = chr(int("27A4", base=16))

def initialize_custom_atm_grid_widgets(cime):

    default_path = Path.home() 
    if cime.cime_output_root is not None:
        if (p := Path(cime.cime_output_root)).exists():
            default_path = p
    
    cv_custom_grid_path = cvars["CUSTOM_GRID_PATH"]
    cv_custom_grid_path.widget = FileChooser(
        path=default_path,
        filename="",
        title="Specify a directory and a new grid name:",
        new_only=True,
        filename_placeholder="Enter new grid name",
        layout={'width': '90%', 'margin': '10px'},
    )

    cv_custom_atm_grid = cvars["CUSTOM_ATM_GRID"]
    cv_custom_atm_grid.widget = MultiCheckbox(
        description="Custom ATM Grid:",
        allow_multi_select=False,
    )

def initialize_custom_ocn_grid_widgets(cime):

    cv_custom_ocn_grid_mode = cvars["OCN_GRID_MODE"]
    cv_custom_ocn_grid_mode.widget = ToggleButtons(
        description="Ocean Grid Mode:",
        layout={"display": "flex", "width": "max-content", "padding": "10px"},
        style={"button_width": "140px", "description_width": description_width},
    )

    cv_custom_ocn_grid = cvars["CUSTOM_OCN_GRID"]
    cv_custom_ocn_grid.widget = MultiCheckbox(
        description="Custom Ocean Grid:",
        allow_multi_select=False,
    )

    cv_ocn_grid_extent = cvars["OCN_GRID_EXTENT"]
    cv_ocn_grid_extent.widget = ToggleButtons(
        description="Grid Extent:",
        layout={"display": "flex", "left":"30px", "width": "max-content", "padding": "5px"},
        style={"button_width": "100px", "description_width": "125px"},
    )

    cv_ocn_cyclic_x = cvars["OCN_CYCLIC_X"]
    cv_ocn_cyclic_x.widget = ToggleButtons(
        description="Zonally Reentrant:",
        layout={"display": "flex", "left":"30px", "width": "max-content", "padding": "5px"},
        style={"button_width": "100px", "description_width": "125px"},
    )

    cv_ocn_nx = cvars["OCN_NX"]
    cv_ocn_nx.widget = Text(
        description="Number of Cells in X direction:",
        layout={"width": "370px", "padding": "5px"},
        style={"description_width": "250px"},
    )

    cv_ocn_ny = cvars["OCN_NY"]
    cv_ocn_ny.widget = Text(
        description="Number of Cells in Y direction:",
        layout={"width": "370px", "padding": "5px"},
        style={"description_width": "250px"},
    )

    cv_ocn_lenx = cvars["OCN_LENX"]
    cv_ocn_lenx.widget = Text(
        description="Grid Length in X direction (degrees):",
        layout={"width": "370px", "padding": "5px"},
        style={"description_width": "250px"},
    )

    cv_ocn_leny = cvars["OCN_LENY"]
    cv_ocn_leny.widget = Text(
        description="Grid Length in Y direction (degrees):",
        layout={"width": "370px", "padding": "5px"},
        style={"description_width": "250px"},
    )

    cv_custom_ocn_grid_name = cvars["CUSTOM_OCN_GRID_NAME"]
    cv_custom_ocn_grid_name.widget = Text(
        description="Custom Ocean Grid Name:",
        layout={"width": "370px", "padding": "5px"},
        style={"description_width": "250px"},
    )

    cv_mom6_bathy_stat = cvars["MOM6_BATHY_STATUS"]
    cv_mom6_bathy_stat.widget = DisabledText(
        value = '',
        disabled = True, 
        description="mom6_bathy status:",
        placeholder = "Incomplete",
        layout={"width": "300px", "padding": "5px", "align_self": "flex-end"},
        style={"description_width": "150px", "background":"lightgray", "text_color":"white"},
    )

def initialize_custom_lnd_grid_widgets(cime):

    description_width = "250px"


    cv_lnd_grid_mode = cvars["LND_GRID_MODE"]
    cv_lnd_grid_mode.widget = ToggleButtons(
        description="LND grid mode:",
        layout={"display": "flex", "width": "max-content", "padding": "10px"},
        style={"button_width": "140px", "description_width": description_width},
    )

    cv_custom_lnd_grid = cvars["CUSTOM_LND_GRID"]
    cv_custom_lnd_grid.widget = MultiCheckbox(
        description="Custom LND Grid:",
        allow_multi_select=False,
    )

    cv_input_mask_mesh = cvars["INPUT_MASK_MESH"]
    cv_input_mask_mesh.widget = FileChooser(
        #path=Path.home(),
        filename="",
        title="&#9658; Mesh file (containing the coordinates):",
        existing_only=True,
        filename_placeholder="Enter new grid name",
        filter_pattern="*.nc",
        layout={'width': '90%', 'margin': '10px'},
    )

    cv_land_mask = cvars["LAND_MASK"]
    cv_land_mask.widget = FileChooser(
        #path=Path.home(),
        filename="",
        title="&#9658; Land mask file (pre-generated by the user and containing a custom land mesh):",
        existing_only=True,
        filename_placeholder="Enter an existing land mask filename",
        filter_pattern="*.nc",
        layout={'width': '90%', 'margin': '10px'},
    )

    cv_lat_var_name = cvars["LAT_VAR_NAME"]
    cv_lat_var_name.widget = Text(
        description_allow_html=True,
        description="&#9658; Latitude Variable Name:",
        layout={"width": "350px", "padding": "5px"},
        style={"description_width": "200px"},
    )

    cv_lon_var_name = cvars["LON_VAR_NAME"]
    cv_lon_var_name.widget = Text(
        description_allow_html=True,
        description="&#9658; Longitude Variable Name:",
        layout={"width": "350px", "padding": "5px"},
        style={"description_width": "200px"},
    )

    cv_lat_dim_name = cvars["LAT_DIM_NAME"]
    cv_lat_dim_name.widget = Text(
        description_allow_html=True,
        description="&#9658; Latitude Dimension Name:",
        layout={"width": "350px", "padding": "5px"},
        style={"description_width": "200px"},
    )

    cv_lon_dim_name = cvars["LON_DIM_NAME"]
    cv_lon_dim_name.widget = Text(
        description_allow_html=True,
        description="&#9658; Longitude Dimension Name:",
        layout={"width": "350px", "padding": "5px"},
        style={"description_width": "200px"},
    )


    cv_mask_mesh_mod_status = cvars["MESH_MASK_MOD_STATUS"]
    cv_mask_mesh_mod_status.widget = DisabledText(value = '',)

    cv_input_fsurdat = cvars["INPUT_FSURDAT"]
    cv_input_fsurdat.widget = FileChooser(
        #path=Path.home(),
        filename="",
        title="&#9658; Input surface data file (fsurdat):",
        existing_only=True,
        filename_placeholder="Enter an existing fsurdat filename",
        filter_pattern="*.nc",
        layout={'width': '90%', 'margin': '10px'},
    )

    cv_fsurdat_area_spec = cvars["FSURDAT_AREA_SPEC"]
    cv_fsurdat_area_spec.widget = FsurdatAreaSpecifier()

    cv_fsurdat_idealized = cvars["FSURDAT_IDEALIZED"]
    cv_fsurdat_idealized.widget = ToggleButtons(
        description_allow_html=True,
        description="&#9658; Idealized Surface Data?",
        layout={"display": "flex", "width": "max-content", "margin": "20px 5px 5px 5px", "left":"70px"},
        style={"button_width": "100px", "description_width": "180px"},
    )

    cv_lnd_dom_pft = cvars["LND_DOM_PFT"]
    cv_lnd_dom_pft.widget = Text(
        description_allow_html=True,
        description='&#9658; PFT/CFT',
        layout={'display':'flex', 'width': 'max-content', 'margin':'5px'},
        style={"description_width": description_width},
    )

    cv_lnd_soil_color = cvars["LND_SOIL_COLOR"]
    cv_lnd_soil_color.widget = Text(
        description_allow_html=True,
        description='&#9658; Soil Color (between 0-20)',
        layout={'display':'flex', 'width': 'max-content', 'margin':'5px'},
        style={"description_width": description_width},
    )

    cv_lnd_std_elev = cvars["LND_STD_ELEV"]
    cv_lnd_std_elev.widget = Text(
        description_allow_html=True,
        description='&#9658; Std. dev. of elevation',
        layout={'display':'flex', 'width': 'max-content', 'margin':'5px'},
        style={"description_width": description_width},
    )

    cv_lnd_max_sat_area = cvars["LND_MAX_SAT_AREA"]
    description_allow_html=True,
    cv_lnd_max_sat_area.widget = Text(
        description_allow_html=True,
        description='&#9658; Max fraction of saturated area',
        layout={'display':'flex', 'width': 'max-content', 'margin':'5px'},
        style={"description_width": description_width, "list_style": "circle"},
    )

    cv_lnd_include_nonveg = cvars["LND_INCLUDE_NONVEG"]
    cv_lnd_include_nonveg.widget = ToggleButtons(
        description_allow_html=True,
        description="&#9658; Include non-vegetation land units?",
        layout={"display": "flex", "width": "max-content", "margin": "5px", 'left':"10px"},
        style={"button_width": "100px", "description_width": "240px"},
    )

    cv_fsurdat_matrix = cvars["FSURDAT_MATRIX"]
    cv_fsurdat_matrix.widget = FsurdatMatrix()

    cv_fsurdat_mod_status = cvars["FSURDAT_MOD_STATUS"]
    cv_fsurdat_mod_status.widget = DisabledText(value='')
