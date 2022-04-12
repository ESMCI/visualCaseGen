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
        ConfigVarStrMS('GRID')
        ConfigVarStr.vdict['GRID'].view_mode = 'suggested' # or 'all'

    def _init_configvar_options(self):
        """ Initialize the options of all ConfigVars by calling their options setters."""
        for varname, var in ConfigVarBase.vdict.items():
            if var.has_options_setter():
                var.refresh_options()

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

        self._btn_grid_view = widgets.Button(
            description='show all grids',
            icon='chevron-down',
            layout = {'display':'none', 'width':'200px', 'margin':'10px'}
        )

        self._create_case = CreateCaseWidget(
            self.ci,
            layout=widgets.Layout(width='800px', border='1px solid silver', padding='10px')
        )


    def _update_grid_view_button(self, change):
        new_compset = change['new']
        if new_compset == "" or new_compset is None:
            self._btn_grid_view.layout.display = 'none'
        else:
            # everytime the compset changes, reset the grid view mode to 'suggested'
            cv_grid = ConfigVarStr.vdict['GRID']
            cv_grid.view_mode = 'suggested'
            self._btn_grid_view.description = 'show all grids'
            self._btn_grid_view.icon = 'chevron-down'
            # turn on the grid view button display
            self._btn_grid_view.layout.display = ''

    def _update_create_case(self, change):
        self._create_case.disable()
        new_grid = change['new']
        if new_grid and len(new_grid)>0:
            compset_text =  ConfigVarBase.vdict["COMPSET"].value 
            self._create_case.enable(compset_text, new_grid)

    def _construct_all_widget_observances(self):

        # Change component phys/options tab whenever a frontend component change is made
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVarStr.vdict['COMP_{}'.format(comp_class)]
            cv_comp._widget.observe(
                self._set_comp_options_tab,
                names='_property_lock',
                type='change')

        cv_compset = ConfigVarBase.vdict["COMPSET"] 
        cv_compset.observe(
            self._update_grid_view_button,
            names='value',
            type='change'
        )

        cv_grid = ConfigVarBase.vdict['GRID']
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
        cv_comp_value = ConfigVarStr.vdict['COMP_{}'.format(comp_class)].value
        if cv_comp_value is not None:
            self._comp_options_tab.set_title(comp_ix, cv_comp_value.upper())
            self._comp_options_tab.selected_index = comp_ix

    def _change_grid_view_mode(self, change=None, new_mode=None):

        cv_grid = ConfigVarStr.vdict['GRID']

        if cv_grid.view_mode == 'all':
            cv_grid.view_mode = 'suggested'
        else:
            cv_grid.view_mode = 'all'
        self._btn_grid_view.icon = 'hourglass-start'
        self._btn_grid_view.description = ''

        # second, update the grid list accordingly
        cv_grid.refresh_options()

        # finally, update the grid view mode button
        if cv_grid.view_mode == 'all':
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
                    self._btn_grid_view
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
            self._create_case
        ])

        return vbx_create_case
