import os, sys
import re
from collections import namedtuple

# import CIME -----------------------------------------------------------
filepath = os.path.dirname(os.path.realpath(__file__)) # path of this module
CIMEROOT = os.path.join(filepath, "../../../")
sys.path.append(os.path.join(CIMEROOT, "scripts", "Tools"))

from standard_script_setup import *
from CIME.case import Case
from CIME.nmlgen import NamelistGenerator
from CIME.utils import expect
from CIME.XML.generic_xml           import GenericXML
from CIME.XML.machines              import Machines
from CIME.XML.pes                   import Pes
from CIME.XML.files                 import Files
from CIME.XML.component             import Component
from CIME.XML.compsets              import Compsets
from CIME.XML.grids                 import Grids
from CIME.YML.compliances           import Compliances

import logging
logger = logging.getLogger(__name__)

Compset = namedtuple('Compset', ['alias', 'lname', 'sci_supported_grids'])

class CIME_interface():
    """CIME_interface class is an interface from visualCaseGen to conventional CIME.

    CIME_interface provides several attributes (data members) as listed below. All CIME_interface methods are intended
    to be called within __init__().

    Attributes
    ----------
    driver : str
        Selected CIME driver: "noupc" or "mct"
    comp_classes : list of str
        List of available component classes, e.g., "ATM", "ICE", etc.
    models : dict of str (with str as keys)
        A mapping from component class to available models, e.g., models["ATM"] = {datm, cam, ...}
    phys_opt : dict of pairs of str (with str keys)
        A mapping from model to pair of available (physics, options), where physics are CAM50, CAM60, etc. and options
        are 4xCO2, 1PCT, etc.
    model_grids: list of tuples
        List of model grids (alias, compset, not_compset)
    compliances : CIME.YML.compliances.Compliances
        An object that encapsulates CIME config variable compliances, i.e., logical constraints regarding
        config variables.
    """

    def __init__(self, driver, loadbar=None):
        # data members
        self.driver = driver            # nuopc or mct
        self.comp_classes = None        # ATM, ICE, etc.
        self.models = dict()            # cam, cice, etc.
        self.comp_phys = dict()         # component physics (CAM50, CAM60, etc.)
        self.comp_options = dict()      # component options(4xCO2, 1PCT, etc.)
        self.model_grids = dict()       # model grids (alias, compset, not_compset)
        self.compsets = dict()          # compsets defined at each component
        self._files = None
        self.cimeroot = CIMEROOT

        # Call _retrieve* methods to populate the data members defined above

        if loadbar: loadbar.value = 0.0
        self._retrieve_CIME_basics()
        for comp_class in self.comp_classes:
            self._retrieve_models(comp_class)
            for model in self.models[comp_class]:
                self._retrieve_model_phys_opt(comp_class,model)

        if loadbar: loadbar.value = 2.0
        self._retrieve_model_grids()

        if loadbar: loadbar.value = 4.0
        self._retrieve_compsets()

        if loadbar: loadbar.value = 6.0
        self._retrieve_machines()

        # Initialize the compliances instance
        if loadbar: loadbar.value = 8.0
        self.compliances = Compliances.from_cime()
        self.compliances.unfold_compliances()

        if loadbar: loadbar.value = 10.0

    def _retrieve_CIME_basics(self):
        """ Determine basic CIME variables and properties, including:
            - driver: 'nuopc' or 'mct'.
            - files: CIME.XML.files instance containing XML files of CIME.
            - comp_classes: The list of component classes, e.g., ATM, OCN, ICE, etc.,
                excluding CPL and ESP.

            Notes
            -----
                CIME basics variables (driver, files, etc.) are defined as CIME_interface module variables
        """

        self._files = Files(comp_interface=self.driver)
        drv_config_file = self._files.get_value("CONFIG_CPL_FILE")
        drv_comp = Component(drv_config_file, "CPL")
        self.comp_classes = drv_comp.get_valid_model_components()
        self.comp_classes = [c for c in self.comp_classes if c not in ['CPL', 'ESP']]

    def _retrieve_model_phys_opt(self, comp_class, model):
        """ Retrieves component physics (CAM60, CICE6, etc.) and options (%SCAM, %ECO, etc) from  config_component.xml
        file from a given comp_class and model. Retrieved physics and options pairs are stored in self.phys_opt dict.

        Parameters
        ----------
        comp_class : str
            component class, e.g., "ATM", "ICE", etc.
        model : str
            model name excluding version number, e.g., "cam", "cice", "mom", etc.
        """

        compatt = {"component": model}
        comp_config_file =  self._files.get_value('CONFIG_{}_FILE'.format(comp_class), compatt)
        if not os.path.exists(comp_config_file):
            logger.error("config file for {} doesn't exist.".format(model))
            return
        compobj = Component(comp_config_file, comp_class)
        rootnode = compobj.get_child("description")
        desc_nodes = compobj.get_children("desc", root=rootnode)

        comp_physics = [] # e.g., CAM60, CICE6, etc.
        comp_all_options = [] # e.g., %SCAM, %ECO, etc.
        comp_physics_desc = []
        comp_options_desc = dict()
        comp_physics_options = dict() # available options for each component physics

        # Go through description entries in config_component.xml nd extract component physics and options:
        for node in desc_nodes:
            physics = compobj.get(node, comp_class.lower())
            option = compobj.get(node, 'option')
            description = compobj.text(node)
            if description[-1]==':':
                description = description[:-1]
            if physics:
                opts = re.findall( r'\[%(.*?)\]',physics)
                if '[%' in physics:
                    physics = physics.split('[%')[0]
                if physics == "CAM[456]0%SCAM": # todo: this is special case -- generalize if possible.
                    comp_options_desc["SCAM"] = description
                    physics = '' # don't store.
                if physics == "CAM":
                    physics = "Specialized"
                if len(physics)>0:
                    comp_physics.append(physics)
                    if len(opts)>0:
                        comp_physics_options[physics] = opts
                if len(opts)==1:
                    # if only one option is provided in a physics description, then store the option description.
                    comp_options_desc[opts[0]] = description
                comp_physics_desc.append(description)
            elif option:
                option = option.strip()
                comp_all_options.append(option)
                comp_options_desc[option] = description

        if len(comp_physics)==0:
            comp_physics.append(model.upper())
            comp_physics_desc.append(model.upper())

        # Model physics
        self.comp_phys[model] = (comp_physics, comp_physics_desc)

        # Model physics options
        self.comp_options[model] = dict()
        for phys in comp_physics:
            # options are defined for this physics.
            if phys in comp_physics_options:
                phys_descriptions = []
                for opt in comp_physics_options[phys]:
                    if opt in comp_options_desc:
                        phys_descriptions.append(comp_options_desc[opt])
                    else:
                        phys_descriptions.append('no description')
                self.comp_options[model][phys] = (
                    comp_physics_options[phys], # phys options
                    phys_descriptions # phys options descriptions
                )
            else: # no options defined for this model physics, so list all model options.
                self.comp_options[model][phys] = (
                    comp_all_options,
                    [comp_options_desc[opt] for opt in comp_all_options] # all option descriptions
                )

    def _retrieve_models(self, comp_class):
        """ Retrieves the available models of a given component class. Retrieved models
        are stored in self.models dict.

        Parameters
        ----------
        comp_class : str
            component class, e.g., "ATM", "ICE", etc.
        """

        # Find list of models for component class
        # List can be in different locations, check CONFIG_XXX_FILE
        comp_config_filename = 'CONFIG_{}_FILE'.format(comp_class)
        _models = self._files.get_components(comp_config_filename)

        # Backup, check COMP_ROOT_DIR_XXX
        root_dir_node_name = 'COMP_ROOT_DIR_' + comp_class
        if (_models is None) or (None in _models):
            _models = self._files.get_components(root_dir_node_name)

        # sanity checks
        assert (_models is not None) and (None not in _models),"Unable to find list of supported components"

        # update models for this comp_class
        self.models[comp_class] = []
        for model in _models:
            compatt = {"component":model}
            logger.debug("Reading CIME XML for model {}...".format(model))
            comp_config_file = self._files.get_value(comp_config_filename, compatt, resolved=False)
            assert comp_config_file is not None,"No component {} found for class {}".format(model, comp_class)
            comp_config_file =  self._files.get_value(comp_config_filename, compatt)
            if not( comp_config_file is not None and os.path.isfile(comp_config_file) ):
                logger.warning("Config file {} for component {} not found.".format(comp_config_file, model))
                continue
            else:
                self.models[comp_class].append(model)

    def _retrieve_model_grids(self):
        self._grids_obj = Grids()
        grids = self._grids_obj.get_child("grids")
        model_grids_xml = self._grids_obj.get_children("model_grid", root=grids)

        self.model_grids = []
        for model_grid in model_grids_xml:
            alias = self._grids_obj.get(model_grid,"alias")
            compset = self._grids_obj.get(model_grid,"compset")
            not_compset = self._grids_obj.get(model_grid,"not_compset")
            desc = ''
            desc_node = self._grids_obj.get_children("desc", root=model_grid)
            if desc_node:
                desc = self._grids_obj.text(desc_node[0])
            self.model_grids.append((alias, compset, not_compset, desc))

    def retrieve_component_grids(self, grid_alias, compset, atmnlev=None, lndnlev=None):
        # todo: implement atmlev and lndnlev
        config_grids = self._grids_obj._read_config_grids(grid_alias, compset, atmnlev, lndnlev)
        # config_grids[0] : long grid name
        return config_grids[1] # dict of component grids, e.g., {'a%': 'T62','l%': 'null','oi%': 'gx1v7', ...}


    def _retrieve_compsets(self):
        cc = self._files.get_components("COMPSETS_SPEC_FILE")

        for component in cc:
            compsets_filename = self._files.get_value("COMPSETS_SPEC_FILE", {"component":component})

            # Check if COMPSET spec file exists
            if (os.path.isfile(compsets_filename)):
                self.compsets[component] = []
                c = Compsets(compsets_filename)
                compsets_xml = c.get_children("compset")
                for compset in compsets_xml:
                    sci_supported_grids = []
                    alias  = c.text(c.get_child("alias", root=compset))
                    lname  = c.text(c.get_child("lname", root=compset))
                    science_support_nodes = c.get_children("science_support", root=compset)
                    for snode in science_support_nodes:
                        sci_supported_grids.append(c.get(snode,"grid"))
                    self.compsets[component].append(Compset(alias,lname, sci_supported_grids))

    def _retrieve_machines(self):
        machs_file = self._files.get_value("MACHINES_SPEC_FILE")
        self.machine = None
        try:
            machines_obj = Machines(machs_file)
            self.machine = machines_obj.machine
            self.machines = machines_obj.list_available_machines()
        except:
            # CIME couldn't determine the machine. Set machine to None and manually determine the list of machines
            machines_obj = GenericXML(machs_file)
            self.machine = None
            # list_available_machines
            self.machines = []
            nodes  = machines_obj.get_children("machine")
            for node in nodes:
                mach = machines_obj.get(node, "MACH")
                self.machines.append(mach)