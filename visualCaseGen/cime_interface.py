import os
import sys
import re
import logging
import socket
import getpass
from collections import namedtuple
from pathlib import Path

# import CIME -----------------------------------------------------------
filepath = os.path.dirname(os.path.realpath(__file__)) # path of this module
CIMEROOT = Path(Path(filepath).parent.parent, 'cime').as_posix()
sys.path.append(os.path.join(CIMEROOT))

from CIME.XML.standard_module_setup import *
from CIME.XML.generic_xml           import GenericXML
from CIME.XML.machines              import Machines
from CIME.XML.files                 import Files
from CIME.XML.component             import Component
from CIME.XML.compsets              import Compsets
from CIME.XML.grids                 import Grids
from CIME.case.case                 import Case

logger = logging.getLogger(__name__)

Compset = namedtuple('Compset', ['alias', 'lname'])

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
    """

    def __init__(self, driver, loadbar=None):
        # data members
        self.driver = driver            # nuopc or mct
        self.comp_classes = None        # ATM, ICE, etc.
        self.models = dict()            # cam, cice, etc.
        self.comp_phys = dict()         # component physics (CAM50, CAM60, etc.)
        self.comp_phys_desc = dict()    # component physics descriptions
        self.comp_options = dict()      # component options(4xCO2, 1PCT, etc.)
        self.comp_options_desc = dict() # component options descriptions
        self.model_grids = dict()       # model grids (alias, compset, not_compset)
        self.compsets = dict()          # compsets defined at each component
        self._files = None
        self._grids_obj = None
        self.din_loc_root = None
        self.cimeroot = CIMEROOT
        self.srcroot = (Path(self.cimeroot).parent).as_posix()

        # Call _retrieve* methods to populate the data members defined above

        def increment_loadbar():
            if loadbar:
                loadbar.value += 2.0
        if loadbar:
            loadbar.value = 0.0

        self._retrieve_cime_basics()
        for comp_class in self.comp_classes:
            self._retrieve_models(comp_class)
            for model in self.models[comp_class]:
                self._retrieve_model_phys_opt(comp_class,model)

        increment_loadbar()
        self._retrieve_model_grids()
        increment_loadbar()
        self._retrieve_compsets()
        increment_loadbar()
        self._retrieve_machines()
        increment_loadbar()
        self._retrieve_clm_fsurdat()
        increment_loadbar()

    def _retrieve_cime_basics(self):
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
            logger.error("config file for %s doesn't exist.", model)
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
        self.comp_phys[model] = comp_physics
        self.comp_phys_desc[model] = comp_physics_desc

        # Model physics options
        for phys in comp_physics:
            # options are defined for this physics.
            if phys in comp_physics_options:
                phys_descriptions = []
                for opt in comp_physics_options[phys]:
                    if opt in comp_options_desc:
                        phys_descriptions.append(comp_options_desc[opt])
                    else:
                        phys_descriptions.append('no description')
                self.comp_options[phys] = comp_physics_options[phys]
                self.comp_options_desc[phys] = phys_descriptions # phys options descriptions
            else: # no options defined for this model physics
                logger.debug("No options defined for physics %s...", phys)
                self.comp_options[phys] = []
                self.comp_options_desc[phys] = []

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
            if model in self.models[comp_class]:
                continue # duplicate
            compatt = {"component":model}
            logger.debug("Reading CIME XML for model %s...", model)
            comp_config_file = self._files.get_value(comp_config_filename, compatt, resolved=False)
            assert comp_config_file is not None,"No component {} found for class {}".format(model, comp_class)
            comp_config_file =  self._files.get_value(comp_config_filename, compatt)
            if not( comp_config_file is not None and os.path.isfile(comp_config_file) ):
                logger.warning("Config file %s for component %s not found.", comp_config_file, model)
                continue
            self.models[comp_class].append(model)

    def _retrieve_model_grids(self):
        self._grids_obj = Grids(comp_interface=self.driver)
        grids = self._grids_obj.get_child("grids")
        model_grid_nodes = self._grids_obj.get_children("model_grid", root=grids)

        self.model_grids = []
        self.component_grids = {comp:set() for comp in self._grids_obj._comp_gridnames}
        for model_grid_node in model_grid_nodes:
            alias = self._grids_obj.get(model_grid_node,"alias")
            compset = self._grids_obj.get(model_grid_node,"compset")
            not_compset = self._grids_obj.get(model_grid_node,"not_compset")
            desc = ''
            desc_node = self._grids_obj.get_children("desc", root=model_grid_node)
            if desc_node:
                desc = self._grids_obj.text(desc_node[0])
            self.model_grids.append((alias, compset, not_compset, desc))
            grid_nodes = self._grids_obj.get_children("grid", root=model_grid_node)
            for grid_node in grid_nodes:
                comp_name = self._grids_obj.get(grid_node, "name")
                value = self._grids_obj.text(grid_node)
                self.component_grids[comp_name].add(value)
        
    def get_domain_properties(self, domain_name):

        if self._grids_obj is None:
            logger.error("In CIME interface module, get_domain_properties called before grids_obj is initialized.") 
        if self.din_loc_root is None:
            logger.error("In CIME interface module, get_domain_properties called before DIN_LOC_ROOT is retrieved.") 

        domain_node = self._grids_obj.get_optional_child(
            "domain",
            attributes = {"name": domain_name},
            root = self._grids_obj.get_child("domains"))

        mesh_nodes = self._grids_obj.get_children("mesh", root=domain_node) 
        if len(mesh_nodes)>1:
            logger.warning(f"Multiples mesh files encountered for the {domain_name} domain.")

        mesh_filepath = self._grids_obj.text(mesh_nodes[0]) 
        mesh_filepath = mesh_filepath.\
            replace('$DIN_LOC_ROOT',self.din_loc_root).\
            replace('${DIN_LOC_ROOT}',self.din_loc_root)
        
        nx_node = self._grids_obj.get_children("nx", root=domain_node)
        nx = self._grids_obj.text(nx_node[0]) 

        ny_node = self._grids_obj.get_children("ny", root=domain_node)
        ny = self._grids_obj.text(ny_node[0]) 

        return {
            'mesh' : mesh_filepath,
            'nx' : nx,
            'ny' : ny
        }

    def get_grid_lname_parts(self, grid_alias, compset, atmnlev=None, lndnlev=None):
        """Returns a dictionary of parts of grid long name for a grid whose alias is provided as the function arg."""

        # todo: implement atmlev and lndnlev
        grid_lname = self._grids_obj._read_config_grids(grid_alias, compset, atmnlev, lndnlev)
        grid_lname_parts = {} # dict of component grids, e.g., {'a%': 'T62','l%': 'null','oi%': 'gx1v7', ...}

        delimiters = re.findall('[a-z]+%', grid_lname) # e.g., ['a%', 'oi%', ...]
        ixbegin = [None] * len(delimiters)
        ixend = [None] * len(delimiters)
        for i, delimiter in enumerate(delimiters):
            ix = grid_lname.index(delimiter) 
            ixbegin[i] = ix + len(delimiter)
            ixend[i-1] = ix - 1
        grid_lname += ' ' # add a padding (for the last comp grid section)
        for i, delimiter in enumerate(delimiters):
            grid_lname_parts[delimiter] = grid_lname[ixbegin[i] : ixend[i]]

        return grid_lname_parts # dict of component grids, e.g., {'a%': 'T62','l%': 'null','oi%': 'gx1v7', ...}


    def _retrieve_compsets(self):
        cc = self._files.get_components("COMPSETS_SPEC_FILE")

        self.sci_supported_grids = {}
        for component in cc:
            compsets_filename = self._files.get_value("COMPSETS_SPEC_FILE", {"component":component})

            # Check if COMPSET spec file exists
            if os.path.isfile(compsets_filename):
                self.compsets[component] = []
                c = Compsets(compsets_filename)
                compsets_xml = c.get_children("compset")
                for compset in compsets_xml:
                    alias  = c.text(c.get_child("alias", root=compset))
                    lname  = c.text(c.get_child("lname", root=compset))
                    science_support_nodes = c.get_children("science_support", root=compset)
                    self.sci_supported_grids[alias] = []
                    for snode in science_support_nodes:
                        self.sci_supported_grids[alias].append(c.get(snode,"grid"))
                    self.compsets[component].append(Compset(alias,lname))

    def _retrieve_machines(self):
        machs_file = self._files.get_value("MACHINES_SPEC_FILE")
        self.machine = None
        self.cime_output_root = None
        self.din_loc_root = None
        self.project_required = {}

        # casper jupyter hub patch
        fqdn = socket.getfqdn()
        if fqdn.startswith('crhtc') and fqdn.endswith('hpc.ucar.edu'):
            self.machine = "casper"

        machines_obj = Machines(machs_file, machine=self.machine)
        self.machine = machines_obj.get_machine_name()
        self.machines = machines_obj.list_available_machines()

        for machine_node in machines_obj.get_children("machine"):
            machine_name = machines_obj.get(machine_node, "MACH")
            if machine_name == self.machine:

                # Determine CIME_OUTPUT_ROOT (scratch space)
                cime_output_root_node = machines_obj.get_child(root=machine_node, name="CIME_OUTPUT_ROOT")
                self.cime_output_root = machines_obj.text(cime_output_root_node)
                self.cime_output_root = self.expand_env_vars(self.cime_output_root)
                if self.cime_output_root is None:
                    logger.error(f"Couldn't determine CIME_OUTPUT_ROOT for {self.machine}")
                if not os.path.exists(self.cime_output_root):
                    logger.error(f"CIME_OUTPUT_ROOT doesn't exist: {self.cime_output_root}")

                # Determine DIN_LOC_ROOT
                din_loc_root_node = machines_obj.get_child(root=machine_node, name="DIN_LOC_ROOT")
                self.din_loc_root = machines_obj.text(din_loc_root_node)
                self.din_loc_root = self.expand_env_vars(self.din_loc_root)
                if self.din_loc_root is None:
                    logger.error(f"Couldn't determine DIN_LOC_ROOT for {self.machine}")
                if not os.path.exists(self.din_loc_root):
                    logger.error(f"DIN_LOC_ROOT doesn't exist: {self.din_loc_root}")

                break

        # Is a PROJECT variable required by this machine?
        for machine_node in machines_obj.get_children("machine"):
            machine_name = machines_obj.get(machine_node, "MACH")
            try:
                project_required_node = machines_obj.get_child(root=machine_node, name="PROJECT_REQUIRED") 
                self.project_required[machine_name] = machines_obj.text(project_required_node).lower() == "true"
            except:
                self.project_required[machine_name] = False

    def _retrieve_clm_fsurdat(self):
        clm_root = Path(Path(CIMEROOT).parent, "components", "clm")
        clm_namelist_defaults_file = Path(clm_root, "bld", "namelist_files", "namelist_defaults_ctsm.xml")
        assert clm_namelist_defaults_file.is_file(), "Cannot find clm namelist file"

        self.clm_fsurdat = {None:{}, '1850':{}, '2000':{}, 'PtVg':{}}

        clm_namelist_xml = GenericXML(clm_namelist_defaults_file.as_posix())
        for fsurdat_node in clm_namelist_xml.get_children("fsurdat"):
            hgrid = clm_namelist_xml.get(fsurdat_node, "hgrid")
            sim_year = clm_namelist_xml.get(fsurdat_node, "sim_year")
            filedir = clm_namelist_xml.text(fsurdat_node)
            self.clm_fsurdat[sim_year][hgrid] = filedir

    def expand_env_vars(self, expr):
        """Given an expression (of type string) read from a CIME xml file, 
        attempt to expand encountered environment variables."""

        # first, attempt to expand any env vars:
        regex = r"\$ENV\{\w+\}"
        matches = re.findall(regex, expr)
        for match in matches:
            var = match[5:-1]
            val = os.getenv(var) 
            if val is not None:
                expr = expr.replace(match, val)

        try:
            user = os.getlogin()
        except OSError:
            user = getpass.getuser()

        # now, attempt to expand any occurences of $USER or ${USER}
        regex = r"\$USER\b"
        expr = re.sub(regex, user, expr)
        regex = r"\$\{USER\}"
        expr = re.sub(regex, user, expr)

        return expr
