import os
import sys
import re
import logging
import socket
import getpass
from collections import namedtuple
from pathlib import Path

# import CIME -----------------------------------------------------------
filepath = os.path.dirname(os.path.realpath(__file__))  # path of this module
CIMEROOT = Path(Path(filepath).parent.parent, "cime").as_posix()
sys.path.append(os.path.join(CIMEROOT))

from CIME.XML.standard_module_setup import *
from CIME.XML.generic_xml import GenericXML
from CIME.XML.machines import Machines
from CIME.XML.files import Files
from CIME.XML.component import Component
from CIME.XML.compsets import Compsets
from CIME.XML.grids import Grids
from CIME.case.case import Case

logger = logging.getLogger(f"  {__name__.split('.')[-1]}")

Compset = namedtuple("Compset", ["alias", "lname", "model"])
Resolution = namedtuple("Resolution", ["alias", "compset", "not_compset", "desc"])
ComponentGrid = namedtuple("ComponentGrid", ["name", "nx", "ny", "mesh", "desc", "compset_constr", "not_compset_constr"])


class CIME_interface:
    """CIME_interface class is an interface from visualCaseGen to conventional CIME. It provides methods to retrieve
    CIME-related information, such as component classes, models, component physics, component options, resolutions,
    from CIME XML files. It also provides methods to retrieve domain properties, grid long name parts, and components
    from compset long name.

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
    resolutions: list of tuples
        List of resolutions (alias, compset, not_compset)
    """

    def __init__(self):
        # data members
        self.driver = "nuopc"
        self.comp_classes = None  # ATM, ICE, etc.
        self.models = dict()  # cam, cice, etc.
        self.comp_phys = dict()  # component physics (CAM50, CAM60, etc.)
        self.comp_phys_desc = dict()  # component physics descriptions
        self.comp_options = dict()  # component options(4xCO2, 1PCT, etc.)
        self.comp_options_desc = dict()  # component options descriptions
        self.resolutions = []  # model grids (alias, compset, not_compset)
        self.compsets = dict()  # default compsets where keys are aliases
        self._files = None
        self._grids_obj = None
        self.din_loc_root = None
        self.cimeroot = CIMEROOT
        self.srcroot = (Path(self.cimeroot).parent).as_posix()

        # Call _retrieve* methods to populate the data members defined above

        self._retrieve_cime_basics()
        for comp_class in self.comp_classes:
            self._retrieve_models(comp_class)
            for model in self.models[comp_class]:
                self._retrieve_model_phys_opt(comp_class, model)

        self._retrieve_domains_and_resolutions()
        self._retrieve_compsets()
        self._retrieve_machines()
        self._retrieve_clm_data()

    def _retrieve_cime_basics(self):
        """Determine basic CIME variables and properties, including:
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
        self.comp_classes = [c for c in self.comp_classes if c not in ["CPL", "ESP"]]

    def _retrieve_model_phys_opt(self, comp_class, model):
        """Retrieves component physics (CAM60, CICE6, etc.) and options (%SCAM, %ECO, etc) from  config_component.xml
        file from a given comp_class and model. Retrieved physics and options pairs are stored in self.phys_opt dict.

        Parameters
        ----------
        comp_class : str
            component class, e.g., "ATM", "ICE", etc.
        model : str
            model name excluding version number, e.g., "cam", "cice", "mom", etc.
        """

        compatt = {"component": model}
        comp_config_file = self._files.get_value(
            "CONFIG_{}_FILE".format(comp_class), compatt
        )
        if not os.path.exists(comp_config_file):
            logger.error("config file for %s doesn't exist.", model)
            return
        compobj = Component(comp_config_file, comp_class)
        rootnode = compobj.get_child("description")
        desc_nodes = compobj.get_children("desc", root=rootnode)

        comp_physics = []  # e.g., CAM60, CICE6, etc.
        comp_all_options = []  # e.g., %SCAM, %ECO, etc.
        comp_physics_desc = []
        comp_options_desc = dict()
        comp_physics_options = dict()  # available options for each component physics

        # Go through description entries in config_component.xml nd extract component physics and options:
        for node in desc_nodes:
            physics = compobj.get(node, comp_class.lower())
            option = compobj.get(node, "option")
            description = compobj.text(node)
            description = description.strip()
            if description[-1] == ":":
                description = description[:-1]
            if physics:
                opts = re.findall(r"\[%(.*?)\]", physics)
                if "[%" in physics:
                    physics = physics.split("[%")[0]
                if (
                    physics == "CAM[456]0%SCAM"
                ):  # todo: this is special case -- generalize if possible.
                    comp_options_desc["SCAM"] = description
                    physics = ""  # don't store.
                if physics == "CAM":
                    physics = "Specialized"
                if len(physics) > 0:
                    comp_physics.append(physics)
                    if len(opts) > 0:
                        comp_physics_options[physics] = opts
                if len(opts) == 1:
                    # if only one option is provided in a physics description, then store the option description.
                    comp_options_desc[opts[0]] = description
                comp_physics_desc.append(description)
            elif option:
                option = option.strip()
                comp_all_options.append(option)
                comp_options_desc[option] = description

        if len(comp_physics) == 0:
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
                        phys_descriptions.append("no description")
                self.comp_options[phys] = comp_physics_options[phys]
                self.comp_options_desc[phys] = (
                    phys_descriptions  # phys options descriptions
                )
            else:  # no options defined for this model physics
                logger.debug("No options defined for physics %s...", phys)
                self.comp_options[phys] = []
                self.comp_options_desc[phys] = []

    def long_comp_desc(self, comp_str):
        """Returns a long description of a component string, e.g., "CAM%SCAM" -> "CAM: Specialized SCAM: Super-parameterized".

        Parameters
        ----------
        comp_str : str
            component string, e.g., "CAM%SCAM"

        Returns
        -------
        str
            long description of the component string, e.g., "CAM: Specialized SCAM: Super-parameterized"
        """

        # Component physics
        comp_phys = comp_str.split("%")[0]

        # Find model for this component physics
        model = None
        for model in self.comp_phys:
            if comp_phys in self.comp_phys[model]:
                break
        assert model is not None, f"Model not found for {comp_str}"

        # Component physics description
        try:
            comp_phys_ix = self.comp_phys[model].index(comp_phys)
            comp_phys_desc = ": " + self.comp_phys_desc[model][comp_phys_ix]
        except (KeyError, IndexError, ValueError):
            comp_phys_desc = ""

        # Component options
        try:
            comp_opt = comp_str.split("%")[1]
            comp_opt_ix = self.comp_options[comp_phys].index(comp_opt)
            comp_opt_desc = ": " + self.comp_options_desc[comp_phys][comp_opt_ix]
        except (KeyError, IndexError, ValueError):
            comp_opt = ""
            comp_opt_desc = ""

        return ' | ' + comp_phys + comp_phys_desc + ' ' + comp_opt + comp_opt_desc

    def long_compset_desc(self, compset):
        """Generates a long description of a given compset long name."""

        compset_lname_split = compset.lname.split("_")
        desc = "Initialization: " + compset_lname_split[0]
        desc += ''.join([self.long_comp_desc(comp_str) for comp_str in compset_lname_split[1:8]])
        if len(compset_lname_split) > 8:
            desc = desc + ' | '.join(compset_lname_split[8:])

        # Denote if the compset is scientifically supported
        if len(self.sci_supported_grids[compset.alias]) > 0:
            desc += ' | '+"(scientifically supported)"

        return desc

    def _retrieve_models(self, comp_class):
        """Retrieves the available models of a given component class. Retrieved models
        are stored in self.models dict.

        Parameters
        ----------
        comp_class : str
            component class, e.g., "ATM", "ICE", etc.
        """

        # Find list of models for component class
        # List can be in different locations, check CONFIG_XXX_FILE
        comp_config_filename = "CONFIG_{}_FILE".format(comp_class)
        _models = self._files.get_components(comp_config_filename)

        # Backup, check COMP_ROOT_DIR_XXX
        root_dir_node_name = "COMP_ROOT_DIR_" + comp_class
        if (_models is None) or (None in _models):
            _models = self._files.get_components(root_dir_node_name)

        # sanity checks
        assert (_models is not None) and (
            None not in _models
        ), "Unable to find list of supported components"

        # update models for this comp_class
        self.models[comp_class] = []
        for model in _models:
            if model in self.models[comp_class]:
                continue  # duplicate
            compatt = {"component": model}
            logger.debug("Reading CIME XML for model %s...", model)
            comp_config_file = self._files.get_value(
                comp_config_filename, compatt, resolved=False
            )
            assert (
                comp_config_file is not None
            ), "No component {} found for class {}".format(model, comp_class)
            comp_config_file = self._files.get_value(comp_config_filename, compatt)
            if not (comp_config_file is not None and os.path.isfile(comp_config_file)):
                logger.debug(
                    "Config file %s for component %s not found.",
                    comp_config_file,
                    model,
                )
                continue
            self.models[comp_class].append(model)

    def _get_domains(self):
        """Reads and returns component grids, i.e., domains, from the CIME XML file. The 
        compset_constr and not_compset_constr attributes of the ComponentGrid object are not
        filled in here, but are filled in later in the _retrieve_component_grid_constraints method
        
        Returns
        -------
        dict
            A dictionary of ComponentGrid objects, where keys are domain names.
        """

        # read component grids, i.e., domains (from component_grids file)
        domains = {}
        domain_nodes = self._grids_obj.get_children("domain", root=self._grids_obj.get_child("domains"))
        for domain_node in domain_nodes:

            # domain name
            name = self._grids_obj.get(domain_node, "name")

            # mesh path
            mesh_nodes = self._grids_obj.get_children("mesh", root=domain_node)
            if len(mesh_nodes) > 1:
                logger.warning(
                    f"Multiples mesh files encountered for the {name} domain."
                )
            mesh_filepath = self._grids_obj.text(mesh_nodes[0]) if mesh_nodes else ''

            # nx, ny
            nx_node = self._grids_obj.get_children("nx", root=domain_node)
            nx = self._grids_obj.text(nx_node[0]) if nx_node else ''
            ny_node = self._grids_obj.get_children("ny", root=domain_node)
            ny = self._grids_obj.text(ny_node[0]) if ny_node else ''

            # domain description and support
            desc = self._grids_obj.text(self._grids_obj.get_child("desc", root=domain_node))
            support = self._grids_obj.get_optional_child("support", root=domain_node)
            support = '. '+self._grids_obj.text(support) if support is not None else ''

            # ComponentGrid object
            domains[name] = ComponentGrid(
                name=name,
                nx=nx,
                ny=ny,
                mesh=mesh_filepath,
                desc=desc+support,
                compset_constr=set(), # to be filled in later
                not_compset_constr=set(), # to be filled in later
            )

        return domains

    def _retrieve_domains_and_resolutions(self):
        """Retrieves and stores component grids and model resolutions from the corresponding CIME 
        XML files. Retrieved resolutions are stored in self.resolutions list and component grids are
        stored in self.domains dict."""

        self._grids_obj = Grids(comp_interface=self.driver)

        # Get the initial (temporary) dict of domains from the component_grids file
        domains = self._get_domains()

        grids = self._grids_obj.get_child("grids")

        # Component grids dict and resolutions list to be populated in the loop below
        self.domains = {comp: {} for comp in self._grids_obj._comp_gridnames}
        self.resolutions = []

        # loop through model grids (resolutions)
        model_grid_nodes = self._grids_obj.get_children("model_grid", root=grids)
        for model_grid_node in model_grid_nodes:
            alias = self._grids_obj.get(model_grid_node, "alias")
            compset = self._grids_obj.get(model_grid_node, "compset")
            not_compset = self._grids_obj.get(model_grid_node, "not_compset")
            desc = ""

            # loop through component grids that are part of this resolution
            all_component_grids_found = True
            grid_nodes = self._grids_obj.get_children("grid", root=model_grid_node)
            for grid_node in grid_nodes:
                comp_name = self._grids_obj.get(grid_node, "name") # e.g., atm, lnd, ocnice, etc.
                comp_grid = self._grids_obj.text(grid_node)
                if comp_grid in domains:
                    if comp_grid not in self.domains[comp_name]:
                        self.domains[comp_name][comp_grid] = ComponentGrid(
                            name=comp_grid,
                            nx=domains[comp_grid].nx,
                            ny=domains[comp_grid].ny,
                            mesh=domains[comp_grid].mesh,
                            desc=domains[comp_grid].desc,
                            compset_constr=set(),
                            not_compset_constr=set(),
                        )
                    domain = self.domains[comp_name][comp_grid]
                    desc += ' | ' + ' ' + comp_name.upper() + ': ' + domain.desc
                    domain.compset_constr.add(compset)
                    domain.not_compset_constr.add(not_compset)
                else:
                    #logger.warning(f"Domain {comp_grid} not found in component_grids file.")
                    all_component_grids_found = False
                    break
    
            if not all_component_grids_found:
                continue

            self.resolutions.append(Resolution(alias, compset, not_compset, desc))
    
        self._process_domain_constraints()

    def _process_domain_constraints(self):
        """Update the compset_constr and not_compset_constr attributes of the ComponentGrid objects in
        the self.domains dict. This method is called after the component grids and resolutions have 
        been retrieved. It updates the compset and not_compset constraints for each domain: If a domain
        is part of one or more resolutions that have no compset/not_compset constraints, then the domain
        is deemed unconstrained. Otherwise, the domain is constrained by the disjunction of the
        compset/not_compset constraints of all the resolutions it is part of.
        """

        for comp_name, domains in self.domains.items():
            for domain_name, domain in domains.items():
                final_compset_constr = ''
                if None not in domain.compset_constr and len(domain.compset_constr) >= 0:
                    final_compset_constr = '|'.join(domain.compset_constr)
                final_not_compset_constr = ''
                if None not in domain.not_compset_constr and len(domain.not_compset_constr) >= 0:
                    final_not_compset_constr = '|'.join(domain.not_compset_constr)
                self.domains[comp_name][domain_name] = domain._replace(
                    compset_constr=final_compset_constr,
                    not_compset_constr=final_not_compset_constr
                )

    def get_grid_lname_parts(self, grid_alias, compset, atmnlev=None, lndnlev=None):
        """Returns a dictionary of parts of grid long name for a grid whose alias is provided as the function arg."""

        # todo: implement atmlev and lndnlev
        grid_lname = self._grids_obj._read_config_grids(
            grid_alias, compset, atmnlev, lndnlev
        )
        grid_lname_parts = (
            {}
        )  # dict of component grids, e.g., {'a%': 'T62','l%': 'null','oi%': 'gx1v7', ...}

        delimiters = re.findall("[a-z]+%", grid_lname)  # e.g., ['a%', 'oi%', ...]
        ixbegin = [None] * len(delimiters)
        ixend = [None] * len(delimiters)
        for i, delimiter in enumerate(delimiters):
            ix = grid_lname.index(delimiter)
            ixbegin[i] = ix + len(delimiter)
            ixend[i - 1] = ix - 1
        grid_lname += " "  # add a padding (for the last comp grid section)
        for i, delimiter in enumerate(delimiters):
            grid_lname_parts[delimiter] = grid_lname[ixbegin[i] : ixend[i]]

        return grid_lname_parts  # dict of component grids, e.g., {'a%': 'T62','l%': 'null','oi%': 'gx1v7', ...}

    def get_components_from_compset_lname(self, compset_lname):
        """Returns a dictionary of components from a given compset long name. The dictionary keys are component classes"""

        components = {comp_class : None for comp_class in self.comp_classes}
        compset_lname_split = compset_lname.split("_")

        assert len(compset_lname_split) >= len(self.comp_classes)+1, f"Invalid compset long name: {compset_lname}"

        for i, comp_class in enumerate(self.comp_classes):
            components[comp_class] = compset_lname_split[i+1]
    
        return components


    def _retrieve_compsets(self):
        cc = self._files.get_components("COMPSETS_SPEC_FILE")

        self.compsets = {}
        self.sci_supported_grids = {}
        for component in cc:
            compsets_filename = self._files.get_value(
                "COMPSETS_SPEC_FILE", {"component": component}
            )

            # Check if COMPSET spec file exists
            if os.path.isfile(compsets_filename):
                c = Compsets(compsets_filename)
                compsets_xml = c.get_children("compset")
                for compset in compsets_xml:
                    alias = c.text(c.get_child("alias", root=compset))
                    lname = c.text(c.get_child("lname", root=compset))
                    science_support_nodes = c.get_children(
                        "science_support", root=compset
                    )
                    self.sci_supported_grids[alias] = []
                    for snode in science_support_nodes:
                        self.sci_supported_grids[alias].append(c.get(snode, "grid"))
                    self.compsets[alias] = Compset(alias, lname, component)

    def _retrieve_machines(self):
        machs_file = self._files.get_value("MACHINES_SPEC_FILE")
        self.machine = None
        self.cime_output_root = None
        self.din_loc_root = None
        self.project_required = {}

        # casper jupyter hub patch
        fqdn = socket.getfqdn()
        if fqdn.startswith("crhtc") and fqdn.endswith("hpc.ucar.edu"):
            self.machine = "casper"

        machines_obj = Machines(machs_file, machine=self.machine)
        self.machine = machines_obj.get_machine_name()
        self.machines = machines_obj.list_available_machines()

        # TODO: although the below loop appears to loop through all machines, it actually doesn't. As of schema 3.0,
        # i.e., since the config_machines.xml file is split into separate files for each machine, the below
        # loop only looks at self.machine (regardless of the if statement: machine_name == self.machine)
        # So, this loop only retrieves the CIME_OUTPUT_ROOT and DIN_LOC_ROOT for the current machine. This should
        # be updated to retrieve the CIME_OUTPUT_ROOT and DIN_LOC_ROOT for all available machines, in case the user
        # wants to switch machines. However, this would also necessitate determining the machine early on in the
        # configuration process, which is not currently done. Note: see the subsequent loop that determines the
        # project_required attribute for all machines properly.

        for machine_node in machines_obj.get_children("machine"):
            machine_name = machines_obj.get(machine_node, "MACH")
            if machine_name == self.machine:

                # Determine CIME_OUTPUT_ROOT (scratch space)
                cime_output_root_node = machines_obj.get_child(
                    root=machine_node, name="CIME_OUTPUT_ROOT"
                )
                self.cime_output_root = machines_obj.text(cime_output_root_node)
                self.cime_output_root = self.expand_env_vars(self.cime_output_root)
                if self.cime_output_root is None:
                    logger.error(
                        f"Couldn't determine CIME_OUTPUT_ROOT for {self.machine}"
                    )
                if not os.path.exists(self.cime_output_root):
                    logger.error(
                        f"CIME_OUTPUT_ROOT doesn't exist: {self.cime_output_root}"
                    )

                # Determine DIN_LOC_ROOT
                din_loc_root_node = machines_obj.get_child(
                    root=machine_node, name="DIN_LOC_ROOT"
                )
                self.din_loc_root = machines_obj.text(din_loc_root_node)
                self.din_loc_root = self.expand_env_vars(self.din_loc_root)
                if self.din_loc_root is None:
                    logger.error(f"Couldn't determine DIN_LOC_ROOT for {self.machine}")
                if not os.path.exists(self.din_loc_root):
                    logger.error(f"DIN_LOC_ROOT doesn't exist: {self.din_loc_root}")

                break
        
        # Keep a record of whether a project id is required for each machine
        for machine in self.machines:
            machines_obj = Machines(machs_file, machine=machine)
            for machine_node in machines_obj.get_children("machine"):
                machine_name = machines_obj.get(machine_node, "MACH")
                try:
                    project_required_node = machines_obj.get_child(
                        root=machine_node, name="PROJECT_REQUIRED"
                    )
                    self.project_required[machine_name] = (
                        machines_obj.text(project_required_node).lower() == "true"
                    )
                except:
                    self.project_required[machine_name] = False

    def _retrieve_clm_data(self):
        """Retrieve clm fsurdat and flanduse data from the namelist_defaults_ctsm.xml file."""
        clm_root = Path(Path(CIMEROOT).parent, "components", "clm")
        clm_namelist_defaults_file = Path(
            clm_root, "bld", "namelist_files", "namelist_defaults_ctsm.xml"
        )
        assert clm_namelist_defaults_file.is_file(), "Cannot find clm namelist file"

        self.clm_fsurdat = {}

        clm_namelist_xml = GenericXML(clm_namelist_defaults_file.as_posix())
        for fsurdat_node in clm_namelist_xml.get_children("fsurdat"):
            hgrid = clm_namelist_xml.get(fsurdat_node, "hgrid")
            sim_year = clm_namelist_xml.get(fsurdat_node, "sim_year")
            filedir = clm_namelist_xml.text(fsurdat_node)
            if sim_year not in self.clm_fsurdat:
                self.clm_fsurdat[sim_year] = {}
            self.clm_fsurdat[sim_year][hgrid] = os.path.join(
                self.din_loc_root.strip(),
                filedir.strip()
            )

        self.clm_flanduse = {}
        for flanduse_node in clm_namelist_xml.get_children("flanduse_timeseries"):
            hgrid = clm_namelist_xml.get(flanduse_node, "hgrid")
            filedir = clm_namelist_xml.text(flanduse_node)
            self.clm_flanduse[hgrid] = os.path.join(
                self.din_loc_root.strip(),
                filedir.strip()
            )

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
