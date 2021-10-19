import os, sys, re
import ipywidgets as widgets

from visualCaseGen.visualCaseGen.config_var import ConfigVar
from visualCaseGen.visualCaseGen.config_var_opt import ConfigVarOpt
from visualCaseGen.visualCaseGen.config_var_opt_ms import ConfigVarOptMS
from visualCaseGen.visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.visualCaseGen.checkbox_multi_widget import CheckboxMultiWidget
from visualCaseGen.visualCaseGen.create_case_widget import CreateCaseWidget
from visualCaseGen.visualCaseGen.header_widget import HeaderWidget
from visualCaseGen.visualCaseGen.OutHandler import handler as owh

import logging
logger = logging.getLogger(__name__)

class GUI_create_custom():

    def __init__(self, ci):
        self.ci = ci
        self._init_configvars()
        self._init_widgets()
        self._construct_all_widget_observances()
        self._compset_text = ''
        self._grid_view_mode = 'suggested' # or 'all'

    def _init_configvars(self):
        """ Initialize the ConfigVar instances to be displayed on the GUI as configurable case variables.
        """
        logger.debug("Initializing ConfigVars...")

        # Create Case
        cv_inittime = ConfigVarOpt('INITTIME')
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVarOpt('COMP_'+str(comp_class))
            cv_comp_phys = ConfigVarOpt('COMP_{}_PHYS'.format(comp_class), never_unset=True)
            cv_comp_option = ConfigVarOptMS('COMP_{}_OPTION'.format(comp_class), always_set=True)
            cv_comp_grid = ConfigVar('{}_GRID'.format(comp_class))
        cv_compset = ConfigVar('COMPSET')
        cv_grid = ConfigVarOptMS('GRID')

    def _init_widgets(self):
        # Create Case: --------------------------------------

        self.comp_labels = []
        for comp_class in self.ci.comp_classes:
            self.comp_labels.append(
                widgets.Label(
                    value = '{} {} {}'.format(
                        chr(int("2000",base=16)), chr(int("25BC",base=16)), comp_class),
                    layout = widgets.Layout(width='105px',display='flex',justify_content='center')
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
                    layout=widgets.Layout(width='105px', max_height='120px')
                )
            cv_comp.widget_style.button_width = '85px'
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
            cv_comp_option.widget = CheckboxMultiWidget(
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
        cv_grid.widget = CheckboxMultiWidget(
             options=[],
             placeholder = '(Finalize Compset First.)',
             description='Compatible Grids:',
             disabled=True,
             allow_multi_select=False,
             #todo layout=widgets.Layout(width='500px')
        )
        #todo cv_grid.widget_style.description_width = '150px'
        cv_grid.valid_opt_icon = chr(int('27A4',base=16))

        self._btn_grid_view = widgets.Button(
            description='show all grids',
            icon='chevron-down',
            layout = {'display':'none', 'width':'200px', 'margin':'10px'}
        )

        self._create_case = CreateCaseWidget(
            self.ci,
            layout=widgets.Layout(width='800px', border='1px solid silver', padding='10px')
        )


    def _update_grid_widget(self):

        cv_grid = ConfigVar.vdict['GRID']
        if self._compset_text==None:
            cv_grid.set_widget_properties({
                'disabled': True,
                'description': 'Compatible Grids:',
                'placeholder': '(Finalize Compset First.)'
            })
            self._btn_grid_view.layout.display = 'none'
        else:
            compatible_grids = []
            grid_descriptions = []
            for alias, compset_attr, not_compset_attr, desc in self.ci.model_grids:
                if compset_attr and not re.search(compset_attr, self._compset_text):
                    continue
                if not_compset_attr and re.search(not_compset_attr, self._compset_text):
                    continue
                if self._grid_view_mode == 'suggested' and desc == '':
                    continue

                # temporarily set grid names:

                comp_grid_dict = self.ci.retrieve_component_grids(alias, self._compset_text)
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
                cv_grid.set_widget_properties({'disabled': True})
                if self._grid_view_mode == 'suggested':
                    cv_grid.set_widget_properties({
                        'placeholder': "Couldn't find any suggested grids. Show all grids or change COMPSET."})
                else:
                    cv_grid.set_widget_properties({
                        'placeholder': 'No compatible grids. Change COMPSET.'})
            else:
                cv_grid.set_widget_properties({
                    'disabled': False,
                    'placeholder': 'Select from {} compatible grids'.format(len(compatible_grids)),
                })
                cv_grid.value = ()
                cv_grid.options = compatible_grids
                cv_grid.tooltips = grid_descriptions

            self._btn_grid_view.layout.display = '' # turn on the display

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
        new_compset_text = ConfigVar.vdict['INITTIME'].value
        for comp_class in self.ci.comp_classes:

            # 0. Component
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            if cv_comp.is_none():
                new_compset_text = ''
                break

            # 1. Component Physics
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            if not cv_comp_phys.is_none():
                comp_phys_val = cv_comp_phys.value
                if comp_phys_val == 'Specialized':
                    comp_phys_val = 'CAM' # todo: generalize this special case
                new_compset_text += '_'+comp_phys_val

                # 2. Component Option (optional)
                cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
                comp_option_val = cv_comp_option.value
                if (not cv_comp_option.is_none()):
                    new_compset_text += '%'+comp_option_val
                else:
                    return # Change not finalized yet. (Otherwise, cv_comp_option would have a value, since we set 
                           # its always_set attribute to True.) Yet, cv_comp_option doesn't have a value now, most 
                           # likely because cv_comp_option is temporarily set to none_val, i.e., ()., before it is
                           # to be set to its actual value. Return for now, without making any changes in compset. 
            else:
                new_compset_text = ''
                break

        new_compset_text = new_compset_text.replace('%(none)','')

        if new_compset_text != self._compset_text:
            cv_compset = ConfigVar.vdict['COMPSET']
            if new_compset_text == '':
                cv_compset.value = f"<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>"
            else:
                cv_compset.value = f"<p style='text-align:right'><b><i>compset: </i><font color='green'>{new_compset_text}</b></p>"
            self._compset_text = new_compset_text
            self._change_grid_view_mode(new_mode='suggested')
            self._update_grid_widget()

    def _update_create_case(self, change):
        assert change['name'] == 'value'
        self._create_case.disable()
        new_grid = change['new']
        if new_grid and len(new_grid)>0:
            self._create_case.enable(self._compset_text, new_grid[0][1:].strip())

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
            self._update_create_case,
            names='value',
            type='change'
        )

        self._btn_grid_view.on_click(self._change_grid_view_mode)

    def _set_comp_options_tab(self, change):
        if change['old'] == {}:
            return # change not finalized yet
        comp_class = change['owner'].description[0:3]
        comp_ix = self.ci.comp_classes.index(comp_class)
        self._comp_options_tab.set_title(comp_ix, ConfigVar.vdict['COMP_{}'.format(comp_class)].value.upper())
        self._comp_options_tab.selected_index = comp_ix

    def _change_grid_view_mode(self, change=None, new_mode=None):

        # first, update the grid_view_mode attribute
        if new_mode:
            # invoked by backend
            self._grid_view_mode = new_mode
        else:
            # invoked by frontend click
            if self._grid_view_mode == 'all':
                self._grid_view_mode = 'suggested'
            else:
                self._grid_view_mode = 'all'
        self._btn_grid_view.icon = 'hourglass-start' 
        self._btn_grid_view.description = '' 

        # second, update the grid list accordingly
        self._update_grid_widget()

        # finally, update the grid view mode button
        if self._grid_view_mode == 'all':
            self._btn_grid_view.description = 'show suggested grids' 
            self._btn_grid_view.icon = 'chevron-up' 
        else:
            self._btn_grid_view.description = 'show all grids' 
            self._btn_grid_view.icon = 'chevron-down' 


    def construct(self):

        def _constr_vbx_components():
            hbx_components = widgets.HBox([ConfigVar.vdict['COMP_{}'.format(comp_class)]._widget for comp_class in self.ci.comp_classes])
            vbx_components = widgets.VBox([widgets.HBox(self.comp_labels), hbx_components])
            vbx_components.layout.border = '1px solid silver'
            vbx_components.layout.width = '800px'
            return vbx_components

            #Component options:
        def _constr_hbx_comp_options():
            self._comp_options_tab = widgets.Tab(layout=widgets.Layout(width="800px"))
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

        def _constr_vbx_grids():
            vbx_grids = widgets.VBox([ConfigVar.vdict['GRID']._widget, self._btn_grid_view],
                layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'center'})
            vbx_grids.layout.border = '1px solid silver'
            vbx_grids.layout.width = '800px'
            return vbx_grids

        ## END -- functions to determine the GUI layout

        vbx_create_case = widgets.VBox([
            ConfigVar.vdict['INITTIME']._widget,
            HeaderWidget("Components:"),
            _constr_vbx_components(),
            HeaderWidget("Physics and Options:"),
            _constr_hbx_comp_options(),
            ConfigVar.vdict['COMPSET']._widget,
            HeaderWidget("Grids:"),
            _constr_vbx_grids(),
            HeaderWidget("Launch:"),
            self._create_case
        ])

        return vbx_create_case
