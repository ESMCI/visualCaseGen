import os
import re

from CIME.case import Case
from CIME.nmlgen import NamelistGenerator
from CIME.utils import expect
from CIME.XML.machines              import Machines
from CIME.XML.pes                   import Pes
from CIME.XML.files                 import Files
from CIME.XML.component             import Component
from CIME.XML.compsets              import Compsets
from CIME.XML.grids                 import Grids

from visualCIME.visualCIME.OutHandler import handler as owh
from visualCIME.visualCIME.ConfigVar import ConfigVar
import ipywidgets as widgets
import logging
logger = logging.getLogger(__name__)

files = None
comp_classes = None

def determine_CIME_basics():
    global files, comp_classes
    driver = 'nuopc'
    files = Files(comp_interface=driver)
    drv_config_file = files.get_value("CONFIG_CPL_FILE")
    drv_comp = Component(drv_config_file, "CPL")
    comp_classes = drv_comp.get_valid_model_components()
    comp_classes = [c for c in comp_classes if c not in ['CPL', 'ESP']]

def get_comp_classes():
    return comp_classes

def get_files():
    return files


def get_comp_desc(comp_class, model, files):
    compatt = {"component": model}
    comp_config_file =  files.get_value('CONFIG_{}_FILE'.format(comp_class), compatt)
    compobj = Component(comp_config_file, comp_class)
    rootnode = compobj.get_child("description")
    desc_nodes = compobj.get_children("desc", root=rootnode)
    comp_modes = []
    comp_options = []
    for node in desc_nodes:
        option = compobj.get(node, 'option')
        comp = compobj.get(node, comp_class.lower())
        if comp:
            comp_new = comp
            if '[%' in comp_new:
                comp_new = comp.split('[%')[0]
            if len(comp_new)>0:
                comp_modes.append(comp_new)
        elif option:
            comp_options.append(option.strip())

    return comp_modes, comp_options

@owh.out.capture()
def read_CIME_xml():

    determine_CIME_basics()
    for comp_class in comp_classes:

        # Find list of models for component class
        # List can be in different locations, check CONFIG_XXX_FILE
        node_name = 'CONFIG_{}_FILE'.format(comp_class)
        models = files.get_components(node_name)

        # Backup, check COMP_ROOT_DIR_XXX
        root_dir_node_name = 'COMP_ROOT_DIR_' + comp_class
        if (models is None) or (None in models):
            models = files.get_components(root_dir_node_name)

        assert (models is not None) and (None not in models),"Unable to find list of supported components"

        # config var COMP_XXX
        cv_comp = ConfigVar('COMP_'+str(comp_class)); cv_comp_options = []
        cv_comp_mode = ConfigVar('COMP_{}_MODE'.format(comp_class)); cp_comp_mode_options = []
        cv_comp_option = ConfigVar('COMP_{}_OPTION'.format(comp_class)); cp_comp_option_options = []

        for model in models:

            logger.debug("Reading CIME XML for model {}...".format(model))

            if model[0]=='x':
                logger.debug("Skipping the dead component {}.".format(model))
                continue

            compatt = {"component":model}
            comp_root_dir = files.get_value(root_dir_node_name, compatt, resolved=True)

            comp_config_file = files.get_value(node_name, compatt, resolved=False)
            assert comp_config_file is not None,"No component {} found for class {}".format(model, comp_class)
            comp_config_file =  files.get_value(node_name, compatt)

            if not( comp_config_file is not None and os.path.isfile(comp_config_file) ):
                logger.warning("Config file {} for component {} not found.".format(comp_config_file, model))
                continue

            if model not in cv_comp_options:
                cv_comp_options.append(model)

            cv_comp_mode_options, cv_comp_option_options = get_comp_desc(comp_class, model, files)

        # COMP_{} widget
        cv_comp.widget = widgets.Select(
                options=cv_comp_options,
                value=None,
                description=comp_class+':',
                disabled=False,
                layout=widgets.Layout(width='145px', height='105px')
            )
        cv_comp.widget.style.description_width = '50px'

        # COMP_{}_MODE widget
        cv_comp_mode.widget = widgets.Dropdown(
                options=[],
                value=None,
                description=comp_class+':',
                disabled=False,
                layout=widgets.Layout(width='145px')
            )
        cv_comp_mode.widget.style.description_width = '50px'

        # COMP_{}_OPTION widget
        cv_comp_option.widget = widgets.Dropdown(
                options=[],
                value=None,
                description=comp_class+':',
                disabled=False,
                layout=widgets.Layout(width='145px')
            )
        cv_comp_option.widget.style.description_width = '50px'


@owh.out.capture()
def update_comp_modes_and_options(change=None):
    if change != None:
        new_val = change['owner'].value
        comp_class = change['owner'].description[0:3]
        cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
        assert re.search("COMP_...", cv_comp.name)
        if (not ConfigVar.value_is_valid(new_val)) or change['old'] == {}:
            logger.debug("No need to update comp modes and options for {}".format(cv_comp.name))
            return

        logger.debug("Updating the modes and options of ConfigVar {} with value={}".format(cv_comp.name, cv_comp.widget.value))
        comp_modes, comp_options = [], []
        if cv_comp.widget.value != None:
            model = ConfigVar.strip_option_status(cv_comp.widget.value)
            files = Files(comp_interface="nuopc")
            comp_modes, comp_options = get_comp_desc(comp_class, model, files)
        comp_options = ['(none)'] + comp_options
        ConfigVar.vdict["COMP_{}_MODE".format(comp_class)].widget.options = comp_modes#[chr(c_base_red+True)+' {}'.format(mode) for mode in comp_modes]
        ConfigVar.vdict["COMP_{}_MODE".format(comp_class)].update_states()
        ConfigVar.vdict["COMP_{}_OPTION".format(comp_class)].widget.options = comp_options
        ConfigVar.vdict["COMP_{}_OPTION".format(comp_class)].update_states()
    else:
        raise NotImplementedError


def construct_all_widget_observances(compliances):

    # Build validity observances:
    ConfigVar.compliances = compliances
    for varname, var in ConfigVar.vdict.items():
        var.observe_value_validity()

    # Build relational observances:
    for varname, var in ConfigVar.vdict.items():
        var.observe_relations()

    # Build options observances for comp_mode and comp_option
    for comp_class in get_comp_classes():
        cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
        cv_comp.update_states()
        cv_comp_mode = ConfigVar.vdict['COMP_{}_MODE'.format(comp_class)]
        #cv_comp_mode.update_states()
        cv_comp_option = ConfigVar.vdict['COMP_{}_MODE'.format(comp_class)]
        #cv_comp_option.update_states()
        cv_comp.widget.observe(
            update_comp_modes_and_options,
            names='_property_lock',
            type='change')
