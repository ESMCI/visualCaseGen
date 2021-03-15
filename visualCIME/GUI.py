import os, sys, re
# import CIME -----------------------------------------------------------
CIMEROOT = "/glade/work/altuntas/cesm.sandboxes/cesm2.2.0_simple/cime"
sys.path.append(os.path.join(CIMEROOT, "scripts", "Tools"))
from standard_script_setup import *
# import Compliances ----------------------------------------------------
from CIME.YML.compliances import Compliances
# import visualCIME modules ---------------------------------------------
from visualCIME.visualCIME import OutHandler
from visualCIME.visualCIME.ConfigVar import ConfigVar
from visualCIME.visualCIME.CIME_interface import read_CIME_xml, get_comp_classes, get_files, construct_all_widget_observances
import ipywidgets as widgets


def _constr_hbx_basics():

    # Basics:
    drp_driver = widgets.Dropdown(
        options=['nuopc','mct'],
        value='nuopc',
        description='Driver:',
        layout={'width': '180px'}, # If the items' names are long
        disabled=False,
    )

    rad_support = widgets.RadioButtons(
                    options=['scientific', 'tested', 'unsupported'],
                    value='unsupported', # Defaults to 'pineapple'
                    #layout={'width': 'max-content'}, # If the items' names are long
                    description='Support Level:',
                    disabled=False
    )
    rad_support.style.description_width = '140px'

    rad_init = ConfigVar.vdict['INITTIME'].widget

    hbx_basics = widgets.HBox([drp_driver, rad_support, rad_init])
    hbx_basics.layout.border = '2px dotted lightgray'

    return hbx_basics

def _constr_hbx_components():
    hbx_components = widgets.HBox([ConfigVar.vdict['COMP_{}'.format(comp_class)].widget for comp_class in get_comp_classes()])
    hbx_components.layout.border = '2px dotted lightgray'
    return hbx_components

def _constr_hbx_comp_modes():
    #Component modes:
    hbx_comp_modes = widgets.HBox([ConfigVar.vdict['COMP_{}_MODE'.format(comp_class)].widget for comp_class in get_comp_classes()])
    hbx_comp_modes.layout.border = '2px dotted lightgray'
    return hbx_comp_modes

    #Component options:
def _constr_hbx_comp_options():
    hbx_comp_options = widgets.HBox([ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)].widget for comp_class in get_comp_classes()])
    hbx_comp_options.layout.border = '2px dotted lightgray'
    return hbx_comp_options

def _constr_hbx_grids():
    hbx_grids = widgets.HBox([widgets.Label(value="Grids options will be displayed here.")])
    hbx_grids.layout.border = '2px dotted lightgray'
    return hbx_grids


def _constr_hbx_case():
    #Case Name
    txt_casename = widgets.Textarea(
        value='',
        placeholder='Type case name',
        description='Case name:',
        disabled=False,
        layout=widgets.Layout(height='30px', width='400px')
    )

    #Create Case:
    btn_create = widgets.Button(
        value=False,
        description='Create new case',
        disabled=False,
        button_style='', # 'success', 'info', 'warning', 'danger' or ''
        tooltip='Description',
        icon='check',
        layout=widgets.Layout(height='30px')
    )
    btn_setup = widgets.Button(
        value=False,
        description='setup',
        disabled=False,
        button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
        tooltip='Description',
        layout=widgets.Layout(height='30px', width='80px')
    )
    btn_build = widgets.Button(
        value=False,
        description='build',
        disabled=False,
        button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
        tooltip='Description',
        layout=widgets.Layout(height='30px', width='80px')
    )
    btn_submit = widgets.Button(
        value=False,
        description='submit',
        disabled=False,
        button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
        tooltip='Description',
        layout=widgets.Layout(height='30px', width='80px')
    )
    #Component options:
    hbx_case = widgets.HBox([txt_casename, btn_create, btn_setup, btn_build, btn_submit])
    return hbx_case


def GUI():

    read_CIME_xml()
    compliances = Compliances.from_cime()
    compliances.unfold_implications()
    construct_all_widget_observances(compliances)

    vbx_create_case = widgets.VBox([
        widgets.Label(value="Basics:"),
        _constr_hbx_basics(),
        widgets.Label(value="Components:"),
        _constr_hbx_components(),
        widgets.Label(value="Component Physics:"),
        _constr_hbx_comp_modes(),                                
        widgets.Label(value="Component Options:"),
        _constr_hbx_comp_options(),
        ConfigVar.vdict['COMPSET'].widget,
        widgets.Label(value="Grids:"),
        _constr_hbx_grids(),
        widgets.Label(value=""),
        _constr_hbx_case()
    ])

    vCIME = widgets.Accordion(
        children=[vbx_create_case,
                  widgets.IntSlider(), 
                  widgets.Text()], 
        titles=('Slider', 'Text'))

    vCIME.set_title(0,'Create Case')
    vCIME.set_title(1,'Customize')
    vCIME.set_title(2,'Batch')

    return vCIME