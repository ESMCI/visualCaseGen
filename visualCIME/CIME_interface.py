import os

from CIME.case import Case
from CIME.nmlgen import NamelistGenerator
from CIME.utils import expect
from CIME.XML.machines              import Machines
from CIME.XML.pes                   import Pes
from CIME.XML.files                 import Files
from CIME.XML.component             import Component
from CIME.XML.compsets              import Compsets
from CIME.XML.grids                 import Grids
from CIME.XML.compliances           import Compliances

from visualCIME.visualCIME.ConfigVar import ConfigVar

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
        cv_comp = ConfigVar('COMP_'+str(comp_class))
    
        for model in models:

            # config var 
            cv_model_desc = ConfigVar(model+'_desc')

            compatt = {"component":model}
            comp_root_dir = files.get_value(root_dir_node_name, compatt, resolved=True)

            comp_config_file = files.get_value(node_name, compatt, resolved=False)
            assert comp_config_file is not None,"No component {} found for class {}".format(model, comp_class)
            comp_config_file =  files.get_value(node_name, compatt)

            if not( comp_config_file is not None and os.path.isfile(comp_config_file) ):
                print("Warning: Config file {} for component {} not found.".format(comp_config_file, model))
                continue

            compobj = Component(comp_config_file, comp_class)

            rootnode = compobj.get_child("description")
            desc_nodes = compobj.get_children("desc", root=rootnode)
            for node in desc_nodes:
                option = compobj.get(node, 'option')
                if option is not None:
                    cv_model_desc.options.add(option)

            cv_comp.options.add(model)