import re
import logging
import ipywidgets as widgets

#todo from visualCaseGen.config_var import ConfigVar
#todo from visualCaseGen.config_var_opt import ConfigVarOpt
#todo from visualCaseGen.config_var_opt_ms import ConfigVarOptMS
from visualCaseGen.config_var_str import ConfigVarStr
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.checkbox_multi_widget import CheckboxMultiWidget
from visualCaseGen.create_case_widget import CreateCaseWidget
from visualCaseGen.header_widget import HeaderWidget
from visualCaseGen.OutHandler import handler as owh
import visualCaseGen.logic_engine as logic
from visualCaseGen.relational_assertions import relational_assertions_setter

logger = logging.getLogger(__name__)

class GUI_create_custom():

    def __init__(self, ci):
        logic.reset()
        ConfigVarStr.reset()
        self.ci = ci
        self._init_configvars()
        self._init_widgets()
        #todo self._construct_all_widget_observances()
        #todo self._compset_text = ''
        #todo self._grid_view_mode = 'suggested' # or 'all'
        logic.add_relational_assertions(relational_assertions_setter, ConfigVarStr.vdict)

    def _init_configvars(self):
        """ Initialize the ConfigVar instances to be displayed on the GUI as configurable case variables.
        Also initializes the options of each ConfigVar
        """
        logger.debug("Initializing ConfigVars...")

        ConfigVarStr('INITTIME',
            options=['1850', '2000', 'HIST'] ,
            tooltips=['Pre-industrial', 'Present day', 'Historical'],
            value='2000'
        )

        for comp_class in self.ci.comp_classes:

            # Components, e.g., COMP_ATM, COMP_OCN, etc.
            ConfigVarStr('COMP_'+str(comp_class),
                options = [model for model in  self.ci.models[comp_class] if model[0] != 'x'],
                value = None
            )
            #todo ConfigVarOpt('COMP_{}_PHYS'.format(comp_class), never_unset=True)
            #todo ConfigVarOptMS('COMP_{}_OPTION'.format(comp_class), always_set=True)
            #todo ConfigVar('{}_GRID'.format(comp_class))
        #todo ConfigVar('MASK_GRID')
        #todo ConfigVar('COMPSET')
        #todo ConfigVarOptMS('GRID')


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

        cv_inittime = ConfigVarStr.vdict['INITTIME']
        cv_inittime.widget = widgets.ToggleButtons(
            description='Initialization Time:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_inittime.widget_style.button_width='50px'
        cv_inittime.widget_style.description_width = '140px'

        for comp_class in self.ci.comp_classes:

            # Get references to ConfigVars whose widgets are to be initialized
            cv_comp = ConfigVarStr.vdict['COMP_{}'.format(comp_class)]
            cv_comp.widget = widgets.ToggleButtons(
                    description=comp_class+':',
                    layout=widgets.Layout(width='105px', max_height='120px'),
                    disabled=False,
                )
            cv_comp.widget_style.button_width = '85px'
            cv_comp.widget_style.description_width = '0px'


    #todo         cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
    #todo         cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
    #todo         cv_comp_grid = ConfigVar.vdict['{}_GRID'.format(comp_class)]

    #todo         # COMP_{}_PHYS widget
    #todo         cv_comp_phys.widget = widgets.ToggleButtons(
    #todo                 options=[],
    #todo                 value=None,
    #todo                 description='{} physics:'.format(comp_class),
    #todo                 disabled=False,
    #todo                 layout=widgets.Layout(width='700px', max_height='100px', visibility='hidden', margin='20px')
    #todo             )
    #todo         cv_comp_phys.widget_style.button_width = '90px'
    #todo         cv_comp_phys.widget_style.description_width = '90px'

    #todo         # COMP_{}_OPTION widget
    #todo         cv_comp_option.widget = CheckboxMultiWidget(
    #todo                 options=[],
    #todo                 value=None,
    #todo                 description=comp_class+':',
    #todo                 disabled=True,
    #todo                 placeholder="Options will be displayed here after a component selection."
    #todo                 #todo layout=widgets.Layout(width='110px', max_height='100px')
    #todo             )
    #todo         #todo cv_comp_option.widget_style.button_width = '90px'
    #todo         #todo cv_comp_option.widget_style.description_width = '0px'
    #todo         cv_comp_option.valid_opt_icon = '%'

    #todo         cv_comp_grid.widget = DummyWidget()

    #todo     cv_mask_grid = ConfigVar.vdict['MASK_GRID']
    #todo     cv_mask_grid.widget = DummyWidget()

    #todo     cv_compset = ConfigVar.vdict['COMPSET']
    #todo     cv_compset.widget = widgets.HTML(value = "<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>")

    #todo     cv_grid = ConfigVar.vdict['GRID']
    #todo     cv_grid.widget = CheckboxMultiWidget(
    #todo          options=[],
    #todo          placeholder = '(Finalize Compset First.)',
    #todo          description='Compatible Grids:',
    #todo          disabled=True,
    #todo          allow_multi_select=False,
    #todo          #todo layout=widgets.Layout(width='500px')
    #todo     )
    #todo     #todo cv_grid.widget_style.description_width = '150px'
    #todo     cv_grid.valid_opt_icon = chr(int('27A4',base=16))

    #todo     self._btn_grid_view = widgets.Button(
    #todo         description='show all grids',
    #todo         icon='chevron-down',
    #todo         layout = {'display':'none', 'width':'200px', 'margin':'10px'}
    #todo     )

    #todo     self._create_case = CreateCaseWidget(
    #todo         self.ci,
    #todo         layout=widgets.Layout(width='800px', border='1px solid silver', padding='10px')
    #todo     )


    #todo def _update_grid_widget(self):

    #todo     cv_grid = ConfigVar.vdict['GRID']
    #todo     if self._compset_text is None:
    #todo         cv_grid.set_widget_properties({
    #todo             'disabled': True,
    #todo             'description': 'Compatible Grids:',
    #todo             'placeholder': '(Finalize Compset First.)'
    #todo         })
    #todo         self._btn_grid_view.layout.display = 'none'
    #todo     else:
    #todo         compatible_grids = []
    #todo         grid_descriptions = []
    #todo         for alias, compset_attr, not_compset_attr, desc in self.ci.model_grids:
    #todo             if compset_attr and not re.search(compset_attr, self._compset_text):
    #todo                 continue
    #todo             if not_compset_attr and re.search(not_compset_attr, self._compset_text):
    #todo                 continue
    #todo             if self._grid_view_mode == 'suggested' and desc == '':
    #todo                 continue

    #todo             # temporarily set grid names:

    #todo             comp_grid_dict = self.ci.retrieve_component_grids(alias, self._compset_text)
    #todo             ConfigVar.vdict['ATM_GRID'].value = comp_grid_dict['a%']
    #todo             ConfigVar.vdict['LND_GRID'].value = comp_grid_dict['l%']
    #todo             ConfigVar.vdict['OCN_GRID'].value = comp_grid_dict['oi%']
    #todo             ConfigVar.vdict['ICE_GRID'].value = comp_grid_dict['oi%']
    #todo             ConfigVar.vdict['ROF_GRID'].value = comp_grid_dict['r%']
    #todo             ConfigVar.vdict['GLC_GRID'].value = comp_grid_dict['g%']
    #todo             ConfigVar.vdict['WAV_GRID'].value = comp_grid_dict['w%']
    #todo             ConfigVar.vdict['MASK_GRID'].value = comp_grid_dict['m%']

    #todo             def _instance_val_getter(cv_name):
    #todo                 val = ConfigVar.vdict[cv_name].value
    #todo                 if val is None:
    #todo                     val = "None"
    #todo                 return val

    #todo             cv_comp_grids = \
    #todo                 [ConfigVar.vdict['{}_GRID'.format(comp_class)] for comp_class in self.ci.comp_classes] +\
    #todo                 [ConfigVar.vdict['MASK_GRID']]

    #todo             assertions_satisfied = True
    #todo             for cv_comp_grid in cv_comp_grids:
    #todo                 for assertion in self.ci.compliances.assertions(cv_comp_grid.name):
    #todo                     try:
    #todo                         cv_comp_grid.compliances.check_assertion(
    #todo                             assertion,
    #todo                             _instance_val_getter,
    #todo                             _instance_val_getter,
    #todo                         )
    #todo                     except AssertionError:
    #todo                         assertions_satisfied = False
    #todo                         break
    #todo             if not assertions_satisfied:
    #todo                 continue
    #todo             compatible_grids.append(alias)
    #todo             grid_descriptions.append(desc)

    #todo         if len(compatible_grids)==0:
    #todo             cv_grid.set_widget_properties({'disabled': True})
    #todo             if self._grid_view_mode == 'suggested':
    #todo                 cv_grid.set_widget_properties({
    #todo                     'placeholder': "Couldn't find any suggested grids. Show all grids or change COMPSET."})
    #todo             else:
    #todo                 cv_grid.set_widget_properties({
    #todo                     'placeholder': 'No compatible grids. Change COMPSET.'})
    #todo         else:
    #todo             cv_grid.set_widget_properties({
    #todo                 'disabled': False,
    #todo                 'placeholder': 'Select from {} compatible grids'.format(len(compatible_grids)),
    #todo             })
    #todo             cv_grid.value = ()
    #todo             cv_grid.options = compatible_grids
    #todo             cv_grid.tooltips = grid_descriptions

    #todo         self._btn_grid_view.layout.display = '' # turn on the display

    #todo @owh.out.capture()
    #todo def _update_comp_phys(self,change=None):
    #todo     if change is not None:
    #todo         # This method must be invoked by a COMP_... change by the user
    #todo         comp_class = change['owner'].description[0:3]
    #todo         cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
    #todo         if (change['owner'].value_status is False or change['old'] == {}):
    #todo             return

    #todo         logger.debug("Updating the physics of ConfigVar %s with value=%s", cv_comp.name, cv_comp.value)
    #todo         comp_phys, comp_phys_desc = [], []
    #todo         if cv_comp.value is not None:
    #todo             model = cv_comp.value
    #todo             comp_phys, comp_phys_desc = self.ci.comp_phys[model]

    #todo         cv_comp_phys = ConfigVar.vdict["COMP_{}_PHYS".format(comp_class)]
    #todo         cv_comp_phys.widget_layout.visibility = 'visible'
    #todo         cv_comp_phys.options = comp_phys
    #todo         cv_comp_phys.tooltips = comp_phys_desc

    #todo         self._update_comp_options(change=None, invoker_phys=cv_comp_phys)
    #todo     else:
    #todo         raise NotImplementedError

    #todo @owh.out.capture()
    #todo def _update_comp_options(self,change=None, invoker_phys=None):

    #todo     cv_comp_phys = None
    #todo     if change is not None:
    #todo         # The method is invoked by a user change in COMP_..._PHYS widget
    #todo         if change['old'] == {}:
    #todo             # Change in owner not finalized yet. Do nothing for now.
    #todo             return
    #todo         if change['owner'].value_status is False:
    #todo             logger.debug("Invalid value, so no need to update comp options for %s", change['owner'].name)
    #todo             return
    #todo         cv_comp_phys = change['owner'].parentCV

    #todo     elif invoker_phys is not None:
    #todo         # The method is invoked by an internal change in COMP_..._PHYS widget
    #todo         if invoker_phys.value_status is False:
    #todo             logger.debug("Invalid value, so no need to update comp options for %s", invoker_phys.name)
    #todo             return
    #todo         if invoker_phys.value is None:
    #todo             return
    #todo         cv_comp_phys = invoker_phys

    #todo     comp_class = cv_comp_phys.description[0:3]
    #todo     logger.debug("Updating the options for phys of %s", comp_class)
    #todo     if cv_comp_phys.value is not None:
    #todo         cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
    #todo         model = cv_comp.value
    #todo         phys = cv_comp_phys.value
    #todo         comp_options, comp_options_desc = self.ci.comp_options[model][phys]

    #todo         comp_options = ['(none)'] + comp_options
    #todo         comp_options_desc = ['no modifiers for the {} physics'.format(phys)] + comp_options_desc

    #todo         cv_comp_option = ConfigVar.vdict["COMP_{}_OPTION".format(comp_class)]
    #todo         #import time
    #todo         #start = time.time()
    #todo         cv_comp_option.options = comp_options
    #todo         cv_comp_option.tooltips = comp_options_desc
    #todo         cv_comp_option.set_widget_properties({'disabled':False})
    #todo         #end = time.time()
    #todo         #print("elapsed: ", end-start)


    #todo @owh.out.capture()
    #todo def _update_compset(self, change=None):
    #todo     new_compset_text = ConfigVar.vdict['INITTIME'].value
    #todo     for comp_class in self.ci.comp_classes:

    #todo         # 0. Component
    #todo         cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
    #todo         if cv_comp.is_none():
    #todo             new_compset_text = ''
    #todo             break

    #todo         # 1. Component Physics
    #todo         cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
    #todo         if not cv_comp_phys.is_none():
    #todo             comp_phys_val = cv_comp_phys.value
    #todo             if comp_phys_val == 'Specialized':
    #todo                 comp_phys_val = 'CAM' # todo: generalize this special case
    #todo             new_compset_text += '_'+comp_phys_val

    #todo             # 2. Component Option (optional)
    #todo             cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
    #todo             comp_option_val = cv_comp_option.value
    #todo             if not cv_comp_option.is_none():
    #todo                 new_compset_text += '%'+comp_option_val
    #todo             else:
    #todo                 return # Change not finalized yet. (Otherwise, cv_comp_option would have a value, since we set
    #todo                        # its always_set attribute to True.) Yet, cv_comp_option doesn't have a value now, most
    #todo                        # likely because cv_comp_option is temporarily set to none_val, i.e., ()., before it is
    #todo                        # to be set to its actual value. Return for now, without making any changes in compset.
    #todo         else:
    #todo             new_compset_text = ''
    #todo             break

    #todo     new_compset_text = new_compset_text.replace('%(none)','')

    #todo     if new_compset_text != self._compset_text:
    #todo         cv_compset = ConfigVar.vdict['COMPSET']
    #todo         if new_compset_text == '':
    #todo             cv_compset.value = "<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>"
    #todo         else:
    #todo             cv_compset.value = f"<p style='text-align:right'><b><i>compset: </i><font color='green'>{new_compset_text}</b></p>"
    #todo         self._compset_text = new_compset_text
    #todo         self._change_grid_view_mode(new_mode='suggested')
    #todo         self._update_grid_widget()

    #todo def _update_create_case(self, change):
    #todo     assert change['name'] == 'value'
    #todo     self._create_case.disable()
    #todo     new_grid = change['new']
    #todo     if new_grid and len(new_grid)>0:
    #todo         self._create_case.enable(self._compset_text, new_grid[0][1:].strip())

    #todo @owh.out.capture()
    #todo def observe_for_options_validity_update(self, cv):
    #todo     for assertion in self.ci.compliances.assertions(cv.name):
    #todo         logger.debug("Observing relations for ConfigVar %s", cv.name)
    #todo         if all(var in ConfigVar.vdict for var in assertion.variables):
    #todo             for var_other in set(assertion.variables)-{cv.name}:
    #todo                 ConfigVar.vdict[var_other].observe(
    #todo                     cv.update_options_validity,
    #todo                     #names='value',
    #todo                     names='_property_lock',
    #todo                     type='change'
    #todo                 )
    #todo                 logger.debug("Added relational observance of %s for %s", var_other, cv.name)

    #todo def _construct_all_widget_observances(self):

    #todo     # Assign the compliances property of all ConfigVar instsances:
    #todo     ConfigVar.compliances = self.ci.compliances

    #todo     # Build relational observances:
    #todo     for var in ConfigVar.vdict.values():
    #todo         if isinstance(var, (ConfigVarOpt, ConfigVarOptMS)):
    #todo             self.observe_for_options_validity_update(var)

    #todo     # Update COMP_{} states
    #todo     for comp_class in self.ci.comp_classes:
    #todo         cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
    #todo         cv_comp.update_options_validity()

    #todo     # Build options observances for comp_phys
    #todo     for comp_class in self.ci.comp_classes:
    #todo         cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
    #todo         cv_comp.observe(
    #todo             self._update_comp_phys,
    #todo             names='_property_lock',
    #todo             type='change')

    #todo     # Build options observances for comp_option
    #todo     for comp_class in self.ci.comp_classes:
    #todo         cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
    #todo         cv_comp_phys.observe(
    #todo             self._update_comp_options,
    #todo             names='_property_lock',
    #todo             type='change')

    #todo     cv_inittime = ConfigVar.vdict['INITTIME']
    #todo     cv_inittime.observe(
    #todo         self._update_compset,
    #todo         names='_property_lock',
    #todo         type='change'
    #todo     )
    #todo     for comp_class in self.ci.comp_classes:
    #todo         cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
    #todo         cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
    #todo         cv_comp_option.observe(
    #todo             self._update_compset,
    #todo             names='value',
    #todo             type='change')

    #todo         cv_comp.observe(
    #todo             self._set_comp_options_tab,
    #todo             names='_property_lock',
    #todo             type='change')

    #todo     cv_grid = ConfigVar.vdict['GRID']
    #todo     cv_grid.observe(
    #todo         self._update_create_case,
    #todo         names='value',
    #todo         type='change'
    #todo     )

    #todo     self._btn_grid_view.on_click(self._change_grid_view_mode)

    #todo def _set_comp_options_tab(self, change):
    #todo     if change['old'] == {}:
    #todo         return # change not finalized yet
    #todo     comp_class = change['owner'].description[0:3]
    #todo     comp_ix = self.ci.comp_classes.index(comp_class)
    #todo     cv_comp_value = ConfigVar.vdict['COMP_{}'.format(comp_class)].value
    #todo     if cv_comp_value is not None:
    #todo         self._comp_options_tab.set_title(comp_ix, cv_comp_value.upper())
    #todo         self._comp_options_tab.selected_index = comp_ix

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
            hbx_components = widgets.HBox([ConfigVarStr.vdict['COMP_{}'.format(comp_class)]._widget\
                 for comp_class in self.ci.comp_classes])
            vbx_components = widgets.VBox([widgets.HBox(self.comp_labels), hbx_components])
            vbx_components.layout.border = '1px solid silver'
            vbx_components.layout.width = '800px'
            return vbx_components

            #Component options:
        def _constr_hbx_comp_options():
            self._comp_options_tab = widgets.Tab(layout=widgets.Layout(width="800px"))
            self._comp_options_tab.children = tuple(
                widgets.VBox([
                    ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]._widget,
                    ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]._widget
                ])
                for comp_class in self.ci.comp_classes
            )
            for i, comp_class in enumerate(self.ci.comp_classes):
                self._comp_options_tab.set_title(i, comp_class)
            return self._comp_options_tab

        def _constr_vbx_grids():
            vbx_grids = widgets.VBox([ConfigVar.vdict['GRID']._widget, self._btn_grid_view],
                layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'center'})
            vbx_grids.layout.border = '1px solid silver'
            vbx_grids.layout.width = '800px'
            return vbx_grids

        ## END -- functions to determine the GUI layout

        vbx_create_case = widgets.VBox([
            ConfigVarStr.vdict['INITTIME']._widget,
            HeaderWidget("Components:"),
            _constr_vbx_components(),
            HeaderWidget("Physics and Options:"),
            #todo _constr_hbx_comp_options(),
            #todo ConfigVar.vdict['COMPSET']._widget,
            HeaderWidget("Grids:"),
            #todo _constr_vbx_grids(),
            HeaderWidget("Launch:"),
            #todo self._create_case
        ])

        return vbx_create_case
