import os, sys, re
import ipywidgets as widgets
import subprocess

from visualCIME.visualCIME.ConfigVar import ConfigVar
from visualCIME.visualCIME.OutHandler import handler as owh

import logging
logger = logging.getLogger(__name__)

class GUI_create_advanced():

    def __init__(self, ci):
        self.ci = ci
        self._init_configvars()
        self._init_widgets()
        self._construct_all_widget_observances()

    def _init_configvars(self):
        """ Initialize the ConfigVar instances to be displayed on the GUI as configurable case variables.
        """
        logger.debug("Initializing ConfigVars...")

        # Create Case
        cv_inittime = ConfigVar('INITTIME')
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar('COMP_'+str(comp_class))
            cv_comp_phys = ConfigVar('COMP_{}_PHYS'.format(comp_class))
            cv_comp_option = ConfigVar('COMP_{}_OPTION'.format(comp_class))
        cv_compset = ConfigVar('COMPSET')
        cv_grid = ConfigVar('GRID')
        cv_casename = ConfigVar('CASENAME')

    def _init_widgets(self):
        # Create Case: --------------------------------------

        self.comp_labels = []
        for comp_class in self.ci.comp_classes:
            self.comp_labels.append(
                widgets.Label(
                    value = '{} {} {}'.format(
                        chr(int("2000",base=16)), chr(int("25BC",base=16)), comp_class),
                    layout = widgets.Layout(width='110px',display='flex',justify_content='center')
                )
            )

        cv_inittime = ConfigVar.vdict['INITTIME']
        cv_inittime.widget = widgets.ToggleButtons(
            options=['1850', '2000', 'HIST'],
            tooltips=['Pre-industrial', 'Present day', 'Historical'],
            value='2000',
            layout={'width': 'max-content'}, # If the items' names are long
            description='Initialization Time:',
            disabled=False
        )
        cv_inittime.widget.style.button_width='50px'
        cv_inittime.widget.style.description_width = '140px'

        for comp_class in self.ci.comp_classes:

            # Get references to ConfigVars whose widgets are to be initialized
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]

            # Determine the list of available models for a given component class. Available physics and options are to be
            # determined right after the model is selected by the user.
            cv_comp_models = []
            for model in self.ci.models[comp_class]:
                if model[0]=='x':
                    logger.debug("Skipping the dead component {}.".format(model))
                    continue
                if model not in cv_comp_models:
                    cv_comp_models.append(model)

            # COMP_{} widget
            cv_comp.widget = widgets.ToggleButtons(
                    options=cv_comp_models,
                    value=None,
                    description=comp_class+':',
                    disabled=False,
                    layout=widgets.Layout(width='110px', max_height='120px')
                )
            cv_comp.widget.style.button_width = '90px'
            cv_comp.widget.style.description_width = '0px'

            # COMP_{}_PHYS widget
            cv_comp_phys.widget = widgets.ToggleButtons(
                    options=[],
                    value=None,
                    description=comp_class+':',
                    disabled=False,
                    layout=widgets.Layout(width='110px', max_height='100px')
                )
            cv_comp_phys.widget.style.button_width = '90px'
            cv_comp_phys.widget.style.description_width = '0px'

            # COMP_{}_OPTION widget
            cv_comp_option.widget = widgets.ToggleButtons(
                    options=[],
                    value=None,
                    description=comp_class+':',
                    disabled=False,
                    layout=widgets.Layout(width='110px', max_height='100px')
                )
            cv_comp_option.widget.style.button_width = '90px'
            cv_comp_option.widget.style.description_width = '0px'

        cv_compset = ConfigVar.vdict['COMPSET']
        cv_compset.widget = widgets.HTML(value = f"<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>")

        cv_grid = ConfigVar.vdict['GRID']
        cv_grid.widget = widgets.Combobox(
             options=[],
             placeholder = '(Finalize Compset First.)',
             description='Compatible Grids:',
             disabled=True,
             layout=widgets.Layout(width='500px')
        )
        cv_grid.widget.style.description_width = '150px'

        cv_casename = ConfigVar.vdict['CASENAME']
        cv_casename.widget = widgets.Textarea(
            value='',
            placeholder='Type case name',
            description='Case name:',
            disabled=True,
            layout=widgets.Layout(height='30px', width='400px')
        )

        #Create Case:
        self.btn_create = widgets.Button(
            value=False,
            description='Create new case',
            disabled=True,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Description',
            icon='check',
            layout=widgets.Layout(height='30px')
        )
        self.btn_setup = widgets.Button(
            value=False,
            description='setup',
            disabled=True,
            button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Description',
            layout=widgets.Layout(height='30px', width='80px')
        )
        self.btn_build = widgets.Button(
            value=False,
            description='build',
            disabled=True,
            button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Description',
            layout=widgets.Layout(height='30px', width='80px')
        )
        self.btn_submit = widgets.Button(
            value=False,
            description='submit',
            disabled=True,
            button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Description',
            layout=widgets.Layout(height='30px', width='80px')
        )

    def _update_grid_widget(self, compset_text=None):

        cv_grid = ConfigVar.vdict['GRID']
        if compset_text==None:
            cv_grid.widget.disabled = True
            cv_grid.widget.description = 'Compatible Grids:'
            cv_grid.widget.placeholder = '(Finalize Compset First.)'
        else:
            compatible_grids = []
            for alias, compset_attr, not_compset_attr in self.ci.model_grids:
                if compset_attr and not re.search(compset_attr, compset_text):
                    continue
                if not_compset_attr and re.search(not_compset_attr, compset_text):
                    continue
                compatible_grids.append(alias)

            if len(compatible_grids)==0:
                cv_grid.widget.disabled = True
                cv_grid.widget.description = 'Compatible Grids:'
                cv_grid.widget.placeholder = 'No compatible grids. Change COMPSET.'
            else:
                cv_grid.widget.disabled = False
                cv_grid.widget.description = 'Compatible Grids:'
                cv_grid.widget.placeholder = 'Select from {} compatible grids'.format(len(compatible_grids))
                cv_grid.widget.value = ''
                cv_grid.widget.options = compatible_grids

    @owh.out.capture()
    def _update_comp_phys_and_options(self,change=None):
        if change != None:
            new_val = change['owner'].value
            comp_class = change['owner'].description[0:3]
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            assert re.search("COMP_...", cv_comp.name)
            if (not ConfigVar.value_is_valid(new_val)) or change['old'] == {}:
                logger.debug("No need to update comp physics and options for {}".format(cv_comp.name))
                return

            logger.debug("Updating the physics and options of ConfigVar {} with value={}".format(cv_comp.name, cv_comp.widget.value))
            comp_phys, comp_options, comp_phys_desc, comp_options_desc = [], [], [], []
            if cv_comp.widget.value != None:
                model = ConfigVar.strip_option_status(cv_comp.widget.value)
                comp_phys, comp_options, comp_phys_desc, comp_options_desc = self.ci.phys_opt[model]

            if len(comp_phys)==0 and cv_comp.widget.value != None:
                comp_phys = [cv_comp.widget.value.upper()]
                comp_phys_desc = comp_phys
            comp_options = ['(none)'] + comp_options
            comp_options_desc = ['(none)'] + comp_options_desc

            cv_comp_phys = ConfigVar.vdict["COMP_{}_PHYS".format(comp_class)]
            cv_comp_phys.update_options(new_options=comp_phys, tooltips=comp_phys_desc, init_value=True)

            cv_comp_option = ConfigVar.vdict["COMP_{}_OPTION".format(comp_class)]
            cv_comp_option.update_options(new_options=comp_options, tooltips=comp_options_desc, init_value=True)
        else:
            raise NotImplementedError

    @owh.out.capture()
    def _update_compset(self,change=None):
        cv_compset = ConfigVar.vdict['COMPSET']
        cv_grid = ConfigVar.vdict['GRID']
        compset_text = ConfigVar.vdict['INITTIME'].get_value()
        for comp_class in self.ci.comp_classes:
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
            comp_phys_val = cv_comp_phys.get_value()
            comp_option_val = cv_comp_option.get_value()
            if comp_phys_val != None:
                compset_text += '_'+comp_phys_val
                if comp_option_val != None and comp_option_val != '(none)':
                    compset_text += '%'+comp_option_val
            else:
                cv_compset.widget.value = f"<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>"
                self._update_grid_widget()
                return
        cv_compset.widget.value = compset_text
        cv_compset.widget.value = f"<p style='text-align:right'><b><i>compset: </i><font color='green'>{compset_text}</b></p>"
        self._update_grid_widget(compset_text)
        self.compset_text = compset_text

    def _update_case_create(self,change):
        cv_casename = ConfigVar.vdict['CASENAME']
        if 'new' in change:
            if 'value' in change['new']:
                value = change['new']['value']
                if isinstance(value,str) and len(value)>0:
                    cv_casename.widget.disabled = False
                    self.btn_create.disabled = False
            else:
                return
        else:
            cv_casename.widget.value = ''
            cv_casename.widget.disabled = True
            self.btn_create.disabled = True

    def _create_case(self, b):

        cv_grid = ConfigVar.vdict["GRID"]
        cv_casename = ConfigVar.vdict["CASENAME"]
        runout = subprocess.run("{}/scripts/create_newcase --res {} --compset {} --case {} --run-unsupported".format(
            self.ci.cimeroot,
            cv_grid.widget.value,
            self.compset_text,
            cv_casename.widget.value
            ),
            shell=True, capture_output=True
        )

        if runout.returncode == 0:
            logger.info("".format(runout.stdout))
            logger.info("SUCCESS: case created at {} ".format(cv_casename.widget.value))
        else:
            logger.critical("ERROR: {} ".format(runout.stderr))


    @owh.out.capture()
    def observe_relations(self, cv):
        for implication in self.ci.compliances.implications(cv.name):
            logger.debug("Observing relations for ConfigVar {}".format(cv.name))
            if all([var in ConfigVar.vdict for var in implication.variables]):
                for var_other in set(implication.variables)-{cv.name}:
                    ConfigVar.vdict[var_other].widget.observe(
                        cv.update_options_validity,
                        #names='value',
                        names='_property_lock',
                        type='change'
                    )
                    logger.debug("Added relational observance of {} for {}".format(var_other,cv.name))

    def _construct_all_widget_observances(self):

        # Assign the compliances property of all ConfigVar instsances:
        ConfigVar.compliances = self.ci.compliances

        # Build validity observances:
        for varname, var in ConfigVar.vdict.items():
            var.observe_value_validity()

        # Build relational observances:
        for varname, var in ConfigVar.vdict.items():
            self.observe_relations(var)

        # Update COMP_{} states
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.update_options_validity()

        # Build options observances for comp_phys and comp_option
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.widget.observe(
                self._update_comp_phys_and_options,
                names='_property_lock',
                type='change')

        cv_inittime = ConfigVar.vdict['INITTIME']
        cv_inittime.widget.observe(
            self._update_compset,
            names='_property_lock',
            type='change'
        )
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.widget.observe(
                self._update_compset,
                names='_property_lock',
                type='change')
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_phys.widget.observe(
                self._update_compset,
                names='_property_lock',
                type='change')
            cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
            cv_comp_option.widget.observe(
                self._update_compset,
                names='_property_lock',
                type='change')

        cv_grid = ConfigVar.vdict['GRID']
        cv_grid.widget.observe(
            self._update_case_create,
            names='_property_lock',
            type='change'
        )

        self.btn_create.on_click(self._create_case)

    def construct(self):

        def _constr_vbx_components():
            hbx_components = widgets.HBox([ConfigVar.vdict['COMP_{}'.format(comp_class)].widget for comp_class in self.ci.comp_classes])
            vbx_components = widgets.VBox([widgets.HBox(self.comp_labels), hbx_components])
            vbx_components.layout.border = '2px dotted lightgray'
            vbx_components.layout.width = '850px'
            return vbx_components

        def _constr_hbx_comp_phys():
            #Component phys:
            hbx_comp_phys = widgets.HBox([ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)].widget for comp_class in self.ci.comp_classes])
            hbx_comp_phys.layout.border = '2px dotted lightgray'
            return hbx_comp_phys

            #Component options:
        def _constr_hbx_comp_options():
            hbx_comp_options = widgets.HBox([ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)].widget for comp_class in self.ci.comp_classes])
            hbx_comp_options.layout.border = '2px dotted lightgray'
            return hbx_comp_options

        def _constr_hbx_grids():
            hbx_grids = widgets.HBox([ConfigVar.vdict['GRID'].widget])
            hbx_grids.layout.border = '2px dotted lightgray'
            return hbx_grids


        def _constr_hbx_case():
            #Case Name
            cv_casename = ConfigVar.vdict['CASENAME']

            #Component options:
            hbx_case = widgets.HBox([cv_casename.widget, self.btn_create, self.btn_setup, self.btn_build,
                                    self.btn_submit])
            return hbx_case
        ## END -- functions to determine the GUI layout

        vbx_create_case = widgets.VBox([
            ConfigVar.vdict['INITTIME'].widget,
            widgets.Label(value="Components:"),
            _constr_vbx_components(),
            widgets.Label(value="Component Physics:"),
            _constr_hbx_comp_phys(),
            widgets.Label(value="Component Options:"),
            _constr_hbx_comp_options(),
            ConfigVar.vdict['COMPSET'].widget,
            widgets.Label(value="Grids:"),
            _constr_hbx_grids(),
            widgets.Label(value=""),
            _constr_hbx_case()
        ])

        return vbx_create_case
