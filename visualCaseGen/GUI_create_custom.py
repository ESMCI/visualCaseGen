import os, sys, re
import ipywidgets as widgets
import subprocess

from visualCaseGen.visualCaseGen.ConfigVar import ConfigVar
from visualCaseGen.visualCaseGen.ConfigVarOpt import ConfigVarOpt
from visualCaseGen.visualCaseGen.ConfigVarOptMS import ConfigVarOptMS
from visualCaseGen.visualCaseGen.DummyWidget import DummyWidget
from visualCaseGen.visualCaseGen.CheckboxMulti import CheckboxMulti
from visualCaseGen.visualCaseGen.OutHandler import handler as owh

import logging
logger = logging.getLogger(__name__)

class GUI_create_custom():

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
        cv_inittime = ConfigVarOpt('INITTIME')
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVarOpt('COMP_'+str(comp_class))
            cv_comp_phys = ConfigVarOpt('COMP_{}_PHYS'.format(comp_class), never_unset=True)
            cv_comp_option = ConfigVarOptMS('COMP_{}_OPTION'.format(comp_class), never_unset=True)
            cv_comp_grid = ConfigVar('{}_GRID'.format(comp_class))
        cv_compset = ConfigVar('COMPSET')
        cv_grid = ConfigVarOptMS('GRID')
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
        cv_inittime.widget_style.button_width='50px'
        cv_inittime.widget_style.description_width = '140px'

        for comp_class in self.ci.comp_classes:

            # Get references to ConfigVars whose widgets are to be initialized
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
            cv_comp_grid = ConfigVar.vdict['{}_GRID'.format(comp_class)]

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
            cv_comp.widget_style.button_width = '90px'
            cv_comp.widget_style.description_width = '0px'

            # COMP_{}_PHYS widget
            cv_comp_phys.widget = widgets.ToggleButtons(
                    options=[],
                    value=None,
                    description='{} physics:'.format(comp_class),
                    disabled=False,
                    layout=widgets.Layout(width='700px', max_height='100px', visibility='hidden', margin='20px')
                )
            cv_comp_phys.widget_style.button_width = '90px'
            cv_comp_phys.widget_style.description_width = '90px'

            # COMP_{}_OPTION widget
            cv_comp_option.widget = CheckboxMulti(
                    options=[],
                    value=None,
                    description=comp_class+':',
                    disabled=True,
                    placeholder="Options will be displayed here after a component selection."
                    #todo layout=widgets.Layout(width='110px', max_height='100px')
                )
            #todo cv_comp_option.widget_style.button_width = '90px'
            #todo cv_comp_option.widget_style.description_width = '0px'
            cv_comp_option.valid_opt_icon = '%'

            cv_comp_grid.widget = DummyWidget()

        cv_compset = ConfigVar.vdict['COMPSET']
        cv_compset.widget = widgets.HTML(value = f"<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>")

        cv_grid = ConfigVar.vdict['GRID']
        cv_grid.widget = CheckboxMulti(
             options=[],
             placeholder = '(Finalize Compset First.)',
             description='Compatible Grids:',
             disabled=True,
             allow_multi_select=False,
             #todo layout=widgets.Layout(width='500px')
        )
        #todo cv_grid.widget_style.description_width = '150px'
        cv_grid.valid_opt_icon = chr(int('27A4',base=16))

        cv_casename = ConfigVar.vdict['CASENAME']
        cv_casename.widget = widgets.Textarea(
            value='',
            placeholder='Type case name',
            description='Case name:',
            disabled=True,
            layout=widgets.Layout(height='30px', width='500px')
        )
        cv_casename.widget_style.description_width = '100px'

        # Machines
        self.drp_machines = widgets.Dropdown(
            options=self.ci.machines,
            value=self.ci.machine,
            layout={'width': 'max-content'}, # If the items' names are long
            description='Machine name:',
            disabled= (self.ci.machine != None)
        )
        self.drp_machines.style.description_width = '100px'

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

        self.create_case_out = widgets.Output(
            layout={'border': '1px solid black'}
        )

    def _update_grid_widget(self, compset_text=None):

        cv_grid = ConfigVar.vdict['GRID']
        if compset_text==None:
            cv_grid.set_widget_properties({
                'disabled': True,
                'description': 'Compatible Grids:',
                'placeholder': '(Finalize Compset First.)'
            })
        else:
            compatible_grids = []
            grid_descriptions = []
            for alias, compset_attr, not_compset_attr, desc in self.ci.model_grids:
                if compset_attr and not re.search(compset_attr, compset_text):
                    continue
                if not_compset_attr and re.search(not_compset_attr, compset_text):
                    continue

                # temporarily set grid names:

                comp_grid_dict = self.ci.retrieve_component_grids(alias, compset_text)
                ConfigVar.vdict['ATM_GRID'].value = comp_grid_dict['a%']
                ConfigVar.vdict['LND_GRID'].value = comp_grid_dict['l%']
                ConfigVar.vdict['OCN_GRID'].value = comp_grid_dict['o%']
                ConfigVar.vdict['ICE_GRID'].value = comp_grid_dict['i%']
                ConfigVar.vdict['ROF_GRID'].value = comp_grid_dict['r%']
                ConfigVar.vdict['GLC_GRID'].value = comp_grid_dict['g%']
                ConfigVar.vdict['WAV_GRID'].value = comp_grid_dict['w%']

                def _instance_val_getter(cvName):
                    val = ConfigVar.vdict[cvName].value
                    if val == None:
                        val = "None"
                    return val

                assertions_satisfied = True
                for comp_class in self.ci.comp_classes:
                    cv_comp_grid = ConfigVar.vdict['{}_GRID'.format(comp_class)]
                    for assertion in self.ci.compliances.assertions(cv_comp_grid.name):
                        try:
                            cv_comp_grid.compliances.check_assertion(
                                assertion,
                                _instance_val_getter,
                                _instance_val_getter,
                            )
                        except AssertionError as e:
                            assertions_satisfied = False
                            break
                if not assertions_satisfied:
                    continue
                else:
                    compatible_grids.append(alias)
                    grid_descriptions.append(desc)

            if len(compatible_grids)==0:
                cv_grid.set_widget_properties({
                    'disabled': True,
                    'placeholder': 'No compatible grids. Change COMPSET.'
                })
            else:
                cv_grid.set_widget_properties({
                    'disabled': False,
                    'placeholder': 'Select from {} compatible grids'.format(len(compatible_grids)),
                })
                cv_grid.value = ()
                cv_grid.options = compatible_grids
                cv_grid.tooltips = grid_descriptions

    @owh.out.capture()
    def _update_comp_phys(self,change=None):
        if change != None:
            # This method must be invoked by a COMP_... change by the user
            comp_class = change['owner'].description[0:3]
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            if (change['owner'].value_status == False or change['old'] == {}):
                return

            logger.debug("Updating the physics of ConfigVar {} with value={}".format(cv_comp.name, cv_comp.value))
            comp_phys, comp_phys_desc = [], []
            if cv_comp.value != None:
                model = cv_comp.value
                comp_phys, comp_phys_desc = self.ci.comp_phys[model]

            if len(comp_phys)==0 and cv_comp.value != None:
                comp_phys = [cv_comp.value.upper()]
                comp_phys_desc = comp_phys

            cv_comp_phys = ConfigVar.vdict["COMP_{}_PHYS".format(comp_class)]
            cv_comp_phys.widget_layout.visibility = 'visible'
            cv_comp_phys.options = comp_phys
            cv_comp_phys.tooltips = comp_phys_desc

            self._update_comp_options(change=None, invoker_phys=cv_comp_phys)
        else:
            raise NotImplementedError

    @owh.out.capture()
    def _update_comp_options(self,change=None, invoker_phys=None):

        cv_comp_phys = None
        if change != None:
            # The method is invoked by a user change in COMP_..._PHYS widget
            if change['old'] == {}:
                # Change in owner not finalized yet. Do nothing for now.
                return
            elif (change['owner'].value_status == False):
                logger.debug("Invalid value, so no need to update comp options for {}".format(change['owner'].name))
                return
            else:
                cv_comp_phys = change['owner'].parentCV
        elif invoker_phys != None:
            # The method is invoked by an internal change in COMP_..._PHYS widget
            if (invoker_phys.value_status == False):
                logger.debug("Invalid value, so no need to update comp options for {}".format(invoker_phys.name))
                return
            elif invoker_phys.value == None:
                return
            cv_comp_phys = invoker_phys

        comp_class = cv_comp_phys.description[0:3]
        logger.debug("Updating the options for phys of {}".format(comp_class))
        if cv_comp_phys.value != None:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            model = cv_comp.value
            phys = cv_comp_phys.value
            comp_options, comp_options_desc = self.ci.comp_options[model][phys]

            comp_options = ['(none)'] + comp_options
            comp_options_desc = ['no modifiers for the {} physics'.format(phys)] + comp_options_desc

            cv_comp_option = ConfigVar.vdict["COMP_{}_OPTION".format(comp_class)]
            #import time
            #start = time.time()
            cv_comp_option.options = comp_options
            cv_comp_option.tooltips = comp_options_desc
            cv_comp_option.set_widget_properties({'disabled':False})
            #end = time.time()
            #print("elapsed: ", end-start)


    @owh.out.capture()
    def _update_compset(self,change=None):
        cv_compset = ConfigVar.vdict['COMPSET']
        compset_text = ConfigVar.vdict['INITTIME'].value
        for comp_class in self.ci.comp_classes:
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            comp_phys_val = cv_comp_phys.value
            if comp_phys_val == 'SIMPLE':
                comp_phys_val = 'CAM' # todo: generalize this special case
            if comp_phys_val != None:
                compset_text += '_'+comp_phys_val
                cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
                comp_option_val = cv_comp_option.value
                if comp_option_val not in [None, ()] and comp_option_val != '(none)':
                    compset_text += '%'+comp_option_val
            else:
                # display warning
                cv_compset.value = f"<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>"
                self._update_grid_widget()
                return
        cv_compset.value = compset_text
        cv_compset.value = f"<p style='text-align:right'><b><i>compset: </i><font color='green'>{compset_text}</b></p>"
        self._update_grid_widget(compset_text)
        self.compset_text = compset_text

    def _reset_case_create(self):
        cv_casename = ConfigVar.vdict['CASENAME']
        cv_casename.value = ""
        cv_casename.set_widget_properties({'disabled': True})
        self.btn_create.disabled = True

    def _update_case_create(self,change):

        assert change['name'] == 'value'
        self._reset_case_create()
        if self.drp_machines.value:
            new_grid = change['new']
            if new_grid and len(new_grid)>0:
                cv_casename = ConfigVar.vdict['CASENAME']
                cv_casename.set_widget_properties({'disabled': False})
                self.btn_create.disabled = False

    def _call_update_case_create(self, change):
        cv_grid = ConfigVar.vdict['GRID']
        if cv_grid.get_widget_property('disabled'):
            return
        if change == None:
            return
        else:
            if change['old'] == {}:
                # Change in owner not finalized yet. Do nothing for now.
                return
            else:
                self._update_case_create({'name':'value', 'new':cv_grid.value})


    def _create_case(self, b):

        cv_grid = ConfigVar.vdict["GRID"]
        cv_casename = ConfigVar.vdict["CASENAME"]
        self.create_case_out.clear_output()
        with self.create_case_out:
            cmd = "{}/scripts/create_newcase --res {} --compset {} --case {} --run-unsupported".format(
                self.ci.cimeroot,
                cv_grid.value,
                self.compset_text,
                cv_casename.value)
            print("Running cmd: {}".format(cmd))
            runout = subprocess.run(cmd, shell=True, capture_output=True)
            if runout.returncode == 0:
                print("".format(runout.stdout))
                print("SUCCESS: case created at {} ".format(cv_casename.value))
            else:
                print(runout.stdout)
                print("ERROR: {} ".format(runout.stderr))


    @owh.out.capture()
    def observe_for_options_validity_update(self, cv):
        for assertion in self.ci.compliances.assertions(cv.name):
            logger.debug("Observing relations for ConfigVar {}".format(cv.name))
            if all([var in ConfigVar.vdict for var in assertion.variables]):
                for var_other in set(assertion.variables)-{cv.name}:
                    ConfigVar.vdict[var_other].observe(
                        cv.update_options_validity,
                        #names='value',
                        names='_property_lock',
                        type='change'
                    )
                    logger.debug("Added relational observance of {} for {}".format(var_other,cv.name))

    def _construct_all_widget_observances(self):

        # Assign the compliances property of all ConfigVar instsances:
        ConfigVar.compliances = self.ci.compliances

        # Build relational observances:
        for varname, var in ConfigVar.vdict.items():
            if isinstance(var, (ConfigVarOpt, ConfigVarOptMS)):
                self.observe_for_options_validity_update(var)

        # Update COMP_{} states
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.update_options_validity()

        # Build options observances for comp_phys
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.observe(
                self._update_comp_phys,
                names='_property_lock',
                type='change')

        # Build options observances for comp_option
        for comp_class in self.ci.comp_classes:
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_phys.observe(
                self._update_comp_options,
                names='_property_lock',
                type='change')

        cv_inittime = ConfigVar.vdict['INITTIME']
        cv_inittime.observe(
            self._update_compset,
            names='_property_lock',
            type='change'
        )
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.observe(
                self._update_compset,
                names='_property_lock',
                type='change')
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_phys.observe(
                self._update_compset,
                names='_property_lock',
                type='change')
            cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
            cv_comp_option.observe(
                self._update_compset,
                names='value',
                type='change')

            cv_comp.observe(
                self._set_comp_options_tab,
                names='_property_lock',
                type='change')

        cv_grid = ConfigVar.vdict['GRID']
        cv_grid.observe(
            self._update_case_create,
            names='value',
            type='change'
        )

        self.drp_machines.observe(
            self._call_update_case_create,
            names='_property_lock',
            type='change'
        )

        self.btn_create.on_click(self._create_case)

    def _set_comp_options_tab(self, change):
        if change['old'] == {}:
            return # change not finalized yet
        comp_class = change['owner'].description[0:3]
        comp_ix = self.ci.comp_classes.index(comp_class)
        self._comp_options_tab.set_title(comp_ix, ConfigVar.vdict['COMP_{}'.format(comp_class)].value.upper())
        self._comp_options_tab.selected_index = comp_ix

    def construct(self):

        def _constr_vbx_components():
            hbx_components = widgets.HBox([ConfigVar.vdict['COMP_{}'.format(comp_class)]._widget for comp_class in self.ci.comp_classes])
            vbx_components = widgets.VBox([widgets.HBox(self.comp_labels), hbx_components])
            vbx_components.layout.border = '2px dotted lightgray'
            vbx_components.layout.width = '840px'
            return vbx_components

            #Component options:
        def _constr_hbx_comp_options():
            self._comp_options_tab = widgets.Tab(layout=widgets.Layout(width="840px"))
            self._comp_options_tab.children = tuple([
                widgets.VBox([
                    ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]._widget,
                    ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]._widget
                ])
                for comp_class in self.ci.comp_classes
            ])
            for i in range(len(self.ci.comp_classes)):
                self._comp_options_tab.set_title(i, self.ci.comp_classes[i])
            return self._comp_options_tab

        def _constr_hbx_grids():
            hbx_grids = widgets.HBox([ConfigVar.vdict['GRID']._widget])
            hbx_grids.layout.border = '2px dotted lightgray'
            return hbx_grids


        def _constr_hbx_case():
            #Case Name
            cv_casename = ConfigVar.vdict['CASENAME']

            #Component options:
            hbx_case = widgets.HBox([cv_casename._widget, self.btn_create])
            return hbx_case
        ## END -- functions to determine the GUI layout

        vbx_create_case = widgets.VBox([
            ConfigVar.vdict['INITTIME']._widget,
            widgets.Label(value="Components:"),
            _constr_vbx_components(),
            widgets.Label(value="Component Physics and Options:"),
            _constr_hbx_comp_options(),
            ConfigVar.vdict['COMPSET']._widget,
            widgets.Label(value="Grids:"),
            _constr_hbx_grids(),
            widgets.Label(value=""),
            self.drp_machines,
            _constr_hbx_case(),
            self.create_case_out
        ])

        return vbx_create_case
