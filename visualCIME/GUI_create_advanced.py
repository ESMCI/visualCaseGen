import os, sys, re
import ipywidgets as widgets
import subprocess

from visualCIME.visualCIME.ConfigVar import ConfigVar
from visualCIME.visualCIME.DummyWidget import DummyWidget
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
            cv_comp_phys = ConfigVar('COMP_{}_PHYS'.format(comp_class), never_unset=True)
            cv_comp_option = ConfigVar('COMP_{}_OPTION'.format(comp_class), never_unset=True)
            cv_comp_grid = ConfigVar('{}_GRID'.format(comp_class))
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

            cv_comp_grid.widget = DummyWidget()

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
            layout=widgets.Layout(height='30px', width='500px')
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

        self.create_case_out = widgets.Output(
            layout={'border': '1px solid black'}
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

                # temporarily set grid names:

                comp_grid_dict = self.ci.retrieve_component_grids(alias, compset_text)
                ConfigVar.vdict['ATM_GRID'].widget.value = comp_grid_dict['a%']
                ConfigVar.vdict['LND_GRID'].widget.value = comp_grid_dict['l%']
                ConfigVar.vdict['OCN_GRID'].widget.value = comp_grid_dict['o%']
                ConfigVar.vdict['ICE_GRID'].widget.value = comp_grid_dict['i%']
                ConfigVar.vdict['ROF_GRID'].widget.value = comp_grid_dict['r%']
                ConfigVar.vdict['GLC_GRID'].widget.value = comp_grid_dict['g%']
                ConfigVar.vdict['WAV_GRID'].widget.value = comp_grid_dict['w%']

                def _instance_val_getter(cvName):
                    val = ConfigVar.vdict[cvName].get_value()
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

            if len(compatible_grids)==0:
                cv_grid.widget.disabled = True
                cv_grid.widget.placeholder = 'No compatible grids. Change COMPSET.'
            else:
                cv_grid.widget.disabled = False
                cv_grid.widget.placeholder = 'Select from {} compatible grids'.format(len(compatible_grids))
                cv_grid.widget.value = ''
                cv_grid.widget.options = compatible_grids

    @owh.out.capture()
    def _update_comp_phys(self,change=None):
        if change != None:
            # This method must be invoked by a COMP_... change by the user
            new_val = change['owner'].value
            comp_class = change['owner'].description[0:3]
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            if (not ConfigVar.value_is_valid(new_val)) or change['old'] == {}:
                logger.debug("No need to update comp physics for {}".format(cv_comp.name))
                return

            logger.debug("Updating the physics of ConfigVar {} with value={}".format(cv_comp.name, cv_comp.widget.value))
            comp_phys, comp_phys_desc = [], []
            if cv_comp.widget.value != None:
                model = ConfigVar.strip_option_status(cv_comp.widget.value)
                comp_phys, comp_phys_desc = self.ci.comp_phys[model]

            if len(comp_phys)==0 and cv_comp.widget.value != None:
                comp_phys = [cv_comp.widget.value.upper()]
                comp_phys_desc = comp_phys

            cv_comp_phys = ConfigVar.vdict["COMP_{}_PHYS".format(comp_class)]
            cv_comp_phys.update_options(new_options=comp_phys, tooltips=comp_phys_desc)

            self._update_comp_options(change=None, new_phys=cv_comp_phys.widget.value, comp_class=comp_class)
        else:
            raise NotImplementedError

    @owh.out.capture()
    def _update_comp_options(self,change=None, new_phys=None, comp_class=None):

        if change != None:
            # The method is invoked by a direct COMP_..._PHYS change by the user
            if change['old'] == {}:
                logger.debug("No need to update comp options for {}".format(comp_class))
                return
            new_phys = change['owner'].value
            comp_class = change['owner'].description[0:3]
        elif new_phys != None:
            # The method is invoked by an indirect change in COMP_..._PHYS widget
            assert comp_class!=None, "If _update_comp_options is called indirectly, comp_class arg must be provided."

        if (not ConfigVar.value_is_valid(new_phys)):
            logger.debug("No need to update comp options for {}".format(comp_class))
            return

        cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
        logger.debug("Updating the options of {} for phys={}".format(comp_class, cv_comp_phys.widget.value))
        new_phys_stripped = ConfigVar.strip_option_status(new_phys)
        if new_phys_stripped != None:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            model = ConfigVar.strip_option_status(cv_comp.widget.value)
            comp_options, comp_options_desc = self.ci.comp_options[model][new_phys_stripped]

            comp_options = ['(none)'] + comp_options
            comp_options_desc = ['(none)'] + comp_options_desc

            cv_comp_option = ConfigVar.vdict["COMP_{}_OPTION".format(comp_class)]
            cv_comp_option.update_options(new_options=comp_options, tooltips=comp_options_desc)


    @owh.out.capture()
    def _update_compset(self,change=None):
        cv_compset = ConfigVar.vdict['COMPSET']
        compset_text = ConfigVar.vdict['INITTIME'].get_value()
        for comp_class in self.ci.comp_classes:
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            comp_phys_val = cv_comp_phys.get_value()
            if comp_phys_val != None:
                compset_text += '_'+comp_phys_val
                cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
                comp_option_val = cv_comp_option.get_value()
                if comp_option_val != None and comp_option_val != '(none)':
                    compset_text += '%'+comp_option_val
            else:
                # display warning
                cv_compset.widget.value = f"<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>"
                self._update_grid_widget()
                return
        cv_compset.widget.value = compset_text
        cv_compset.widget.value = f"<p style='text-align:right'><b><i>compset: </i><font color='green'>{compset_text}</b></p>"
        self._update_grid_widget(compset_text)
        self.compset_text = compset_text

    def _reset_case_create(self):
        cv_casename = ConfigVar.vdict['CASENAME']
        cv_casename.widget.value = ""
        cv_casename.widget.disabled = True
        self.btn_create.disabled = True

    def _update_case_create(self,change):

        assert change['name'] == 'value'
        self._reset_case_create()
        new_grid = change['new']
        print(new_grid)
        if new_grid and len(new_grid)>0:
            cv_casename = ConfigVar.vdict['CASENAME']
            cv_casename.widget.disabled = False
            self.btn_create.disabled = False

    def _create_case(self, b):

        cv_grid = ConfigVar.vdict["GRID"]
        cv_casename = ConfigVar.vdict["CASENAME"]
        self.create_case_out.clear_output()
        with self.create_case_out:
            cmd = "{}/scripts/create_newcase --res {} --compset {} --case {} --run-unsupported".format(
                self.ci.cimeroot,
                cv_grid.widget.value,
                self.compset_text,
                cv_casename.widget.value)
            print("Running cmd: {}".format(cmd))
            runout = subprocess.run(cmd, shell=True, capture_output=True)
            if runout.returncode == 0:
                print("".format(runout.stdout))
                print("SUCCESS: case created at {} ".format(cv_casename.widget.value))
            else:
                print(runout.stdout)
                print("ERROR: {} ".format(runout.stderr))


    @owh.out.capture()
    def observe_relations(self, cv):
        for assertion in self.ci.compliances.assertions(cv.name):
            logger.debug("Observing relations for ConfigVar {}".format(cv.name))
            if all([var in ConfigVar.vdict for var in assertion.variables]):
                for var_other in set(assertion.variables)-{cv.name}:
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

        # Build options observances for comp_phys
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.widget.observe(
                self._update_comp_phys,
                names='_property_lock',
                type='change')

        # Build options observances for comp_option
        for comp_class in self.ci.comp_classes:
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_phys.widget.observe(
                self._update_comp_options,
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
            names='value',
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
            hbx_case = widgets.HBox([cv_casename.widget, self.btn_create])
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
            _constr_hbx_case(),
            self.create_case_out
        ])

        return vbx_create_case
