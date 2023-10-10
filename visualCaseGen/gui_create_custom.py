import logging
import ipywidgets as widgets
import uuid

from visualCaseGen.config_var import ConfigVar, cvars
from visualCaseGen.init_configvars import init_configvars
from visualCaseGen.sdb import SDB
from visualCaseGen.checkbox_multi_widget import CheckboxMultiWidget
from visualCaseGen.custom_grid_widget import CustomGridWidget
from visualCaseGen.create_case_widget import CreateCaseWidget
from visualCaseGen.header_widget import HeaderWidget
from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.logic import logic

logger = logging.getLogger('\t'+__name__.split('.')[-1])

class GUI_create_custom():

    def __init__(self, ci):
        self.session_id = str(uuid.uuid1())[:8]
        self.sdb = SDB(self.session_id, owner=True)
        self.ci = ci
        ConfigVar.reset()
        init_configvars(self.ci)
        logic.initialize(cvars, self.ci)
        self._init_configvar_options()
        self._init_widgets()
        self._construct_all_widget_observances()
        # set inittime to its default value
        cvars['INITTIME'].value = '2000'

    def _init_configvar_options(self):
        """ Initialize the options of all ConfigVars by calling their options setters."""
        for varname, var in cvars.items():
            if var.has_options_spec():
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

        cv_inittime = cvars['INITTIME']
        cv_inittime.widget = widgets.ToggleButtons(
            description='Initialization Time:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_inittime.widget.style.button_width='50px'
        cv_inittime.widget.style.description_width = '140px'

        for comp_class in self.ci.comp_classes:

            # Get references to ConfigVars whose widgets are to be initialized
            cv_comp = cvars['COMP_{}'.format(comp_class)]
            cv_comp.widget = widgets.ToggleButtons(
                    description=comp_class+':',
                    layout=widgets.Layout(width='105px', max_height='120px'),
                    disabled=False,
                )
            cv_comp.widget.style.button_width = '85px'
            cv_comp.widget.style.description_width = '0px'


            cv_comp_phys = cvars['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_phys.widget = widgets.ToggleButtons(
                    description='{} physics:'.format(comp_class),
                    layout=widgets.Layout(width='700px', max_height='100px', display='none', margin='20px'),
                    disabled=False,
                )
            cv_comp_phys.widget.style.button_width = '90px'
            cv_comp_phys.widget.style.description_width = '90px'

            cv_comp_option = cvars['COMP_{}_OPTION'.format(comp_class)]
            cv_comp_option.widget = CheckboxMultiWidget(
                    description=comp_class+':',
                    placeholder="Options will be displayed here after a component selection.",
                    disabled=True,
                    #todo layout=widgets.Layout(width='110px', max_height='100px')
                )
            #todo cv_comp_option.widget.style.button_width = '90px'
            #todo cv_comp_option.widget.style.description_width = '0px'
            cv_comp_option.valid_opt_char = '%'

        cv_compset = cvars["COMPSET"] 
        cv_compset.value = ""
        cv_compset.widget = widgets.HTML(
            "<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>"
        )

        cv_grid_mode = cvars['GRID_MODE']
        cv_grid_mode.value = "Predefined"
        cv_grid_mode.widget = widgets.ToggleButtons(
            description='Grid Selection Mode:',
            layout={'width': 'max-content', 'margin':'15px'}, # If the items' names are long
            disabled=False,
        )
        cv_grid_mode.widget.style.button_width = '100px'
        cv_grid_mode.widget.style.description_width = '130px'

        cv_grid = cvars['GRID']
        cv_grid._widget.value = ()
        cv_grid.widget = CheckboxMultiWidget(
            options=[],
            placeholder = '(A list of grids will appear here once the compset is finalized.)',
            description='Compatible Grids:',
            disabled=True,
            allow_multi_select=False,
            #todo layout=widgets.Layout(width='500px')
        )
        #todo cv_grid.widget.style.description_width = '150px'
        cv_grid.valid_opt_char = chr(int('27A4',base=16))

        self._btn_grid_view = widgets.Button(
            description='show all grids',
            icon='chevron-down',
            layout = {'display':'none', 'width':'200px', 'margin':'10px'}
        )

        self._custom_grid = CustomGridWidget(self.session_id, self.ci)

        self._vbx_grid_inner = widgets.VBox(
            children=(cv_grid.widget, self._btn_grid_view),
            layout={'display':'flex','flex_flow':'column','align_items':'center'}
        )

        self._create_case = CreateCaseWidget(
            self.ci,
            self.session_id,
            layout=widgets.Layout(width='800px', border='1px solid silver', padding='10px')
        )


    def _on_compset_change(self, change):
        new_compset = change['new']
        self.sdb.update({'compset':new_compset})
        if new_compset == "" or new_compset is None:
            self._btn_grid_view.layout.display = 'none'
        else:
            # everytime the compset changes, reset the grid view mode to 'suggested'
            cv_grid = cvars['GRID']
            cv_grid.view_mode = 'suggested'
            self._btn_grid_view.description = 'show all grids'
            self._btn_grid_view.icon = 'chevron-down'
            # turn on the grid view button display
            self._btn_grid_view.layout.display = ''
    
    def _on_grid_mode_change(self, change):

        new_grid_mode = change['new'] # Predefined | Custom
        cv_grid = cvars['GRID']
        compset_text =  cvars["COMPSET"].value 

        if new_grid_mode == "Predefined":
            self._create_case.disable()
            self._custom_grid.turn_off()
            if compset_text in [None, '']:
                self._vbx_grid_inner.children = ()
            self._vbx_grid_inner.children = (
                cv_grid.widget,
                self._btn_grid_view,
            )

        elif new_grid_mode == "Custom":
            cv_grid.value = None
            self._custom_grid.turn_on()
            self._vbx_grid_inner.children = (
                self._custom_grid,
            )
            self._create_case.enable(compset_text, "custom")

        else:
            raise RuntimeError(f"unknown grid mode: {new_grid_mode}")

    def _on_cv_grid_change(self, change):

        self._create_case.disable()
        new_grid = change['new']
        if new_grid and len(new_grid)>0:
            compset_text =  cvars["COMPSET"].value 
            self._create_case.enable(compset_text, new_grid)

    def _construct_all_widget_observances(self):

        # Change component phys/options tab whenever a frontend component change is made
        for comp_class in self.ci.comp_classes:
            cv_comp = cvars['COMP_{}'.format(comp_class)]
            cv_comp._widget.observe(
                self._set_comp_options_tab,
                names='_property_lock',
                type='change')

        cv_compset = cvars["COMPSET"] 
        cv_compset.observe(
            self._on_compset_change,
            names='value',
            type='change'
        )

        cv_grid_mode = cvars['GRID_MODE']
        cv_grid_mode.observe(
            self._on_grid_mode_change,
            names = 'value',
            type = 'change'
        )

        cv_grid = cvars['GRID']
        cv_grid.observe(
            self._on_cv_grid_change,
            names='value',
            type='change'
        )

        self._btn_grid_view.on_click(self._change_grid_view_mode)

    def _set_comp_options_tab(self, change):
        if change['old'] == {}:
            return # change not finalized yet
        comp_class = change['owner'].description[0:3]
        comp_ix = self.ci.comp_classes.index(comp_class)
        cv_comp_value = cvars['COMP_{}'.format(comp_class)].value
        if cv_comp_value is not None:
            self._comp_options_tab.set_title(comp_ix, cv_comp_value.upper())
            self._comp_options_tab.selected_index = comp_ix

    def _change_grid_view_mode(self, change=None, new_mode=None):

        cv_grid = cvars['GRID']

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
            hbx_components = widgets.HBox([cvars['COMP_{}'.format(comp_class)]._widget\
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
                    cvars['COMP_{}_PHYS'.format(comp_class)]._widget,
                    cvars['COMP_{}_OPTION'.format(comp_class)]._widget
                ])
                for comp_class in self.ci.comp_classes
            )
            for i, comp_class in enumerate(self.ci.comp_classes):
                self._comp_options_tab.set_title(i, comp_class)
            return self._comp_options_tab

        def _constr_vbx_grids():
            vbx_grids = widgets.VBox([
                    cvars['GRID_MODE']._widget,
                    self._vbx_grid_inner
                ],
                layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'center'})
            vbx_grids.layout.border = '1px solid silver'
            vbx_grids.layout.width = '800px'
            return vbx_grids

        ## END -- functions to determine the GUI layout

        vbx_create_case = widgets.VBox([
            cvars['INITTIME']._widget,
            HeaderWidget("Components:"),
            _constr_vbx_components(),
            HeaderWidget("Physics and Options:"),
            _constr_hbx_comp_options(),
            cvars['COMPSET']._widget,
            HeaderWidget("Grids:"),
            _constr_vbx_grids(),
            HeaderWidget("Launch:"),
            self._create_case
        ])

        return vbx_create_case
