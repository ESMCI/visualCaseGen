import re
import logging
import ipywidgets as widgets

from visualCaseGen.config_var_base import ConfigVarBase
from visualCaseGen.config_var_str import ConfigVarStr
from visualCaseGen.config_var_str_ms import ConfigVarStrMS
from visualCaseGen.config_var_compset import ConfigVarCompset
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.checkbox_multi_widget import CheckboxMultiWidget
from visualCaseGen.create_case_widget import CreateCaseWidget
from visualCaseGen.header_widget import HeaderWidget
from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.relational_assertions import relational_assertions_setter
from visualCaseGen.options_dependencies import get_options_setters

logger = logging.getLogger('\t'+__name__.split('.')[-1])

class GUI_create_custom():

    def __init__(self, ci):
        ConfigVarBase.reset()
        self.ci = ci
        self._init_configvars()
        options_setters = get_options_setters(ConfigVarBase.vdict, self.ci)
        ConfigVarBase.determine_interdependencies(
            relational_assertions_setter,
            options_setters)
        self._init_configvar_options()
        self._init_widgets()
        self._construct_all_widget_observances()
        self._grid_view_mode = 'suggested' # or 'all'
        # set inittime to its default value
        ConfigVarStr.vdict['INITTIME'].value = '2000'

    def _init_configvars(self):
        """ Define the ConfigVars and, by doing so, register them with the logic engine. """
        logger.debug("Initializing ConfigVars...")

        ConfigVarStr('INITTIME')
        for comp_class in self.ci.comp_classes:
            ConfigVarStr('COMP_'+str(comp_class))
            ConfigVarStr('COMP_{}_PHYS'.format(comp_class), always_set=True)
            ConfigVarStrMS('COMP_{}_OPTION'.format(comp_class), always_set=True)
            ConfigVarStr('{}_GRID'.format(comp_class))
        ConfigVarCompset("COMPSET", always_set=True)
        ConfigVarStr('MASK_GRID')
        ConfigVarStr('GRID')

    def _init_configvar_options(self):
        """ Initialize the options of all ConfigVars by calling their options setters."""
        for varname, var in ConfigVarBase.vdict.items():
            if var.has_options_setter():
                var.run_options_setter()

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


            cv_comp_phys = ConfigVarStr.vdict['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_phys.widget = widgets.ToggleButtons(
                    description='{} physics:'.format(comp_class),
                    layout=widgets.Layout(width='700px', max_height='100px', visibility='hidden', margin='20px'),
                    disabled=False,
                )
            cv_comp_phys.widget_style.button_width = '90px'
            cv_comp_phys.widget_style.description_width = '90px'

            cv_comp_option = ConfigVarStrMS.vdict['COMP_{}_OPTION'.format(comp_class)]
            cv_comp_option.widget = CheckboxMultiWidget(
                    description=comp_class+':',
                    placeholder="Options will be displayed here after a component selection.",
                    disabled=True,
                    #todo layout=widgets.Layout(width='110px', max_height='100px')
                )
            #todo cv_comp_option.widget_style.button_width = '90px'
            #todo cv_comp_option.widget_style.description_width = '0px'
            cv_comp_option.valid_opt_char = '%'

    #todo         cv_comp_grid = ConfigVar.vdict['{}_GRID'.format(comp_class)]
    #todo         cv_comp_grid.widget = DummyWidget()

    #todo     cv_mask_grid = ConfigVar.vdict['MASK_GRID']
    #todo     cv_mask_grid.widget = DummyWidget()

        cv_compset = ConfigVarBase.vdict["COMPSET"] 
        cv_compset.value = ""
        cv_compset.widget = widgets.HTML(
            "<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>"
        )

        cv_grid = ConfigVarStr.vdict['GRID']
        cv_grid._widget.value = ()
        cv_grid.widget = CheckboxMultiWidget(
            options=[],
            placeholder = '(Finalize Compset First.)',
            description='Compatible Grids:',
            disabled=True,
            allow_multi_select=False,
            #todo layout=widgets.Layout(width='500px')
        )
        #todo cv_grid.widget_style.description_width = '150px'
        cv_grid.valid_opt_char = chr(int('27A4',base=16))

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

    def _construct_all_widget_observances(self):

        # Change component phys/options tab whenever a frontend component change is made
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVarStr.vdict['COMP_{}'.format(comp_class)]
            cv_comp._widget.observe(
                self._set_comp_options_tab,
                names='_property_lock',
                type='change')

    #todo     cv_grid = ConfigVar.vdict['GRID']
    #todo     cv_grid.observe(
    #todo         self._update_create_case,
    #todo         names='value',
    #todo         type='change'
    #todo     )

    #todo     self._btn_grid_view.on_click(self._change_grid_view_mode)

    def _set_comp_options_tab(self, change):
        if change['old'] == {}:
            return # change not finalized yet
        comp_class = change['owner'].description[0:3]
        comp_ix = self.ci.comp_classes.index(comp_class)
        cv_comp_value = ConfigVarStr.vdict['COMP_{}'.format(comp_class)].value
        if cv_comp_value is not None:
            self._comp_options_tab.set_title(comp_ix, cv_comp_value.upper())
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
                    ConfigVarStr.vdict['COMP_{}_PHYS'.format(comp_class)]._widget,
                    ConfigVarStr.vdict['COMP_{}_OPTION'.format(comp_class)]._widget
                ])
                for comp_class in self.ci.comp_classes
            )
            for i, comp_class in enumerate(self.ci.comp_classes):
                self._comp_options_tab.set_title(i, comp_class)
            return self._comp_options_tab

        def _constr_vbx_grids():
            vbx_grids = widgets.VBox([
                    ConfigVarStr.vdict['GRID']._widget,
                    #todo self._btn_grid_view
                ],
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
            _constr_hbx_comp_options(),
            ConfigVarBase.vdict['COMPSET']._widget,
            HeaderWidget("Grids:"),
            _constr_vbx_grids(),
            HeaderWidget("Launch:"),
            #todo self._create_case
        ])

        return vbx_create_case
