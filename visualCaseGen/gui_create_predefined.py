import re
import logging
import ipywidgets as widgets

from visualCaseGen.config_var import ConfigVar
from visualCaseGen.config_var_str import ConfigVarStr
from visualCaseGen.config_var_str_ms import ConfigVarStrMS
from visualCaseGen.config_var_compset import ConfigVarCompset
from visualCaseGen.checkbox_multi_widget import CheckboxMultiWidget
from visualCaseGen.create_case_widget import CreateCaseWidget
from visualCaseGen.header_widget import HeaderWidget
from visualCaseGen.options_dependencies import get_options_setters

logger = logging.getLogger(__name__)

class GUI_create_predefined():

    def __init__(self, ci):
        ConfigVar.reset()
        self.ci = ci
        self._init_configvars()
        # an empty relational assertions setter
        relational_assertions_setter = lambda cvars:{}
        # an options_setter list with a single entry: GRID
        options_setters = [os for os in get_options_setters(ConfigVar.vdict, self.ci) if os.var.name == "GRID"]
        ConfigVar.determine_interdependencies(
            relational_assertions_setter,
            options_setters)
        self._init_configvar_options()
        self._init_widgets()
        self._construct_all_widget_observances()
        self._update_compsets(None)
        self._available_compsets = []

    def _init_configvars(self):

        ConfigVarStr('INITTIME')
        for comp_class in self.ci.comp_classes:
            # Note, COMP_???_FILTER are the only component-related variables shown in the frontend.
            # The rest of the component-related variables are either used at backend or not used at all,
            # but need to be defined so as to parse the option_setters and relational assertions.
            ConfigVarStr('COMP_{}_FILTER'.format(comp_class))
            ConfigVarStr('COMP_'+str(comp_class))
            ConfigVarStr('COMP_{}_PHYS'.format(comp_class), always_set=True)
            ConfigVarStrMS('COMP_{}_OPTION'.format(comp_class), always_set=True)
            ConfigVarStr('{}_GRID'.format(comp_class))

        ConfigVarStr("COMPSET", always_set=True)
        ConfigVarStr('MASK_GRID')
        ConfigVarStrMS('GRID')
        ConfigVarStr.vdict['GRID'].view_mode = 'suggested' # or 'all'

    def _init_configvar_options(self):
        """ Initialize the options of all ConfigVars by calling their options setters."""
        for varname, var in ConfigVar.vdict.items():
            if var.has_options_setter():
                var.refresh_options()

        for comp_class in self.ci.comp_classes:
            cv_comp_filter = ConfigVar.vdict['COMP_{}_FILTER'.format(comp_class)]
            cv_comp_filter_options = ['any']
            for model in self.ci.models[comp_class]:
                if model[0]=='x':
                    logger.debug("Skipping the dead component %s", model)
                    continue
                if model.upper() == 'D'+comp_class.strip() or model.upper() == 'S'+comp_class:
                    continue # will add to end
                if model not in cv_comp_filter_options:
                    cv_comp_filter_options.append(model)
            cv_comp_filter_options += ['data', 'none']
            cv_comp_filter.options = cv_comp_filter_options
            cv_comp_filter.value = cv_comp_filter.options[0]

    def _init_widgets(self):

        self.scientific_only_widget = widgets.Checkbox(
            value=False,
            #layout={'width': 'max-content'}, # If the items' names are long
            description='Scientifically supported configs only',
            disabled=False,
            layout=widgets.Layout(left='-40px', margin='10px', width='500px')
        )

        self.comp_labels = []
        for comp_class in self.ci.comp_classes:
            self.comp_labels.append(
                widgets.Label(
                    value = '{} {} {}'.format(
                        chr(int("2000",base=16)), chr(int("25BC",base=16)), comp_class),
                    layout = widgets.Layout(width='105px',display='flex',justify_content='center')
                )
            )

        for comp_class in self.ci.comp_classes:
            cv_comp_filter = ConfigVar.vdict['COMP_{}_FILTER'.format(comp_class)]
            cv_comp_filter.widget = widgets.ToggleButtons(
                description=comp_class,
                disabled=False,
                layout=widgets.Layout(width='105px', max_height='120px')
            )
            cv_comp_filter.widget_style.button_width = '85px'
            cv_comp_filter.widget_style.description_width = '0px'

        self.keywords_widget = widgets.Textarea(
            value = '',
            placeholder = 'Type keywords to filter compsets below',
            description = "Keywords:",
            disabled=False,
            layout=widgets.Layout(height='30px', width='500px', padding='10px')
        )
        self.keywords_widget.style.description_width = '90px'

        cv_compset = ConfigVar.vdict['COMPSET']
        cv_compset.widget = widgets.Dropdown(
            options=[],
            description='Compset:',
            disabled=True,
            layout=widgets.Layout(width='650px', padding='10px')
        )
        cv_compset.widget_style.description_width = '90px'
        cv_compset.valid_opt_icon = chr(int('27A4',base=16))

        self.compset_desc_widget = widgets.Label("", layout = {'left':'160px', 'margin':'10px'})

        cv_grid = ConfigVar.vdict['GRID']
        cv_grid._widget.value = ()
        cv_grid.widget = CheckboxMultiWidget(
             options=[],
             placeholder = '(Finalize Compset First.)',
             description='Compatible Grids:',
             disabled=True,
             allow_multi_select=False,
             #todo layout=widgets.Layout(width='500px')
        )
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

    def _update_compsets(self, b):

        # First, reset both the compset and the grid widgets:
        cv_compset = ConfigVar.vdict['COMPSET']

        # Now, determine all available compsets
        self._available_compsets = []

        if self.scientific_only_widget.value is True:
            # add scientifically supported compsets only
            for component in self.ci.compsets:
                for compset in self.ci.compsets[component]:
                    if len(compset.sci_supported_grids)>0:
                        self._available_compsets.append(compset)
        else:
            # add all compsets regardless of support level
            for component in self.ci.compsets:
                self._available_compsets += self.ci.compsets[component]

        filter_compsets = []
        for comp_class in self.ci.comp_classes:
            cv_comp_filter = ConfigVar.vdict['COMP_{}_FILTER'.format(comp_class)]
            filter_compsets.append((comp_class,cv_comp_filter.value))


        new_available_compsets = []
        for compset in self._available_compsets:
            filter_compset = False
            for comp_class, model in filter_compsets:
                if model == "any":
                    pass
                elif (model == "none" and 'S'+comp_class not in compset.lname) or\
                     (model == "data" and 'D'+comp_class not in compset.lname) or\
                     (model not in ["none", "data"] and model.upper() not in compset.lname):
                    filter_compset = True
                    break

            if not filter_compset:
                new_available_compsets.append(compset)
        self._available_compsets = new_available_compsets


        if self.keywords_widget.value != '':
            keywords = self.keywords_widget.value.split(',')
            new_available_compsets = []
            for ac in self._available_compsets:
                all_keywords_found = True
                for keyword in keywords:
                    keyword = keyword.strip()
                    if keyword in ac[1] or keyword in ac[0]:
                        pass
                    else:
                        all_keywords_found = False
                        break
                if all_keywords_found:
                    new_available_compsets.append(ac)
            self._available_compsets = new_available_compsets

        available_compsets_str = ['{}: {}'.format(ac.alias, ac.lname) for ac in self._available_compsets]

        cv_compset.options = available_compsets_str
        cv_compset.set_widget_properties({'disabled': False })
        n_available_compsets = len(cv_compset.options)
        if n_available_compsets > 0:
            self.compset_desc_widget.value = '{} Select from {} available compsets above.'.\
                format(chr(int("2191",base=16)), n_available_compsets)
        else:
            self.compset_desc_widget.value = '{} Cannot find any compsets with the above filters/keywords.'.\
                format(chr(int("2757",base=16)))

    def _update_grid_view_button(self, change):
        new_compset = change['new']
        cv_grid = ConfigVarStr.vdict['GRID']
        if new_compset == "" or new_compset is None:
            self._btn_grid_view.layout.display = 'none'
            cv_grid.options = []
        else:
            # everytime the compset changes, reset the grid view mode to 'suggested'
            cv_grid.view_mode = 'suggested'
            self._btn_grid_view.description = 'show all grids'
            self._btn_grid_view.icon = 'chevron-down'
            # turn on the grid view button display
            self._btn_grid_view.layout.display = ''

    def _change_grid_view_mode(self, b):

        cv_grid = ConfigVar.vdict['GRID']

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


    def _update_create_case(self, change):
        self._create_case.disable()
        new_grid = change['new']
        if new_grid and len(new_grid)>0:
            compset_text = ConfigVar.vdict['COMPSET'].value.split(':')[0]
            self._create_case.enable(compset_text, new_grid)

    def _construct_all_widget_observances(self):

        self.scientific_only_widget.observe(
            self._update_compsets,
            names='value'
        )

        cv_compset = ConfigVar.vdict['COMPSET']
        cv_compset.observe(
            self._update_grid_view_button,
            names='value',
            type='change'
        )

        cv_grid = ConfigVar.vdict['GRID']
        cv_grid.observe(
            self._update_create_case,
            names='value',
            type='change'
        )

        for comp_class in self.ci.comp_classes:
            cv_comp_filter = ConfigVar.vdict['COMP_{}_FILTER'.format(comp_class)]
            cv_comp_filter.observe(
                self._update_compsets,
                names='value',
                type='change'
            )

        self.keywords_widget.observe(
            self._update_compsets,
            names='_property_lock',
            type='change'
        )

        self._btn_grid_view.on_click(self._change_grid_view_mode)

    def construct(self):

        hbx_comp_labels = widgets.HBox(self.comp_labels)
        hbx_comp_modes = widgets.HBox([ConfigVar.vdict['COMP_{}_FILTER'.format(comp_class)]._widget\
             for comp_class in self.ci.comp_classes], layout={'overflow':'hidden'})
        hbx_comp_modes.layout.width = '800px'

        vbx_compset = widgets.VBox([
            hbx_comp_labels,
            hbx_comp_modes,
            self.keywords_widget,
            ConfigVar.vdict['COMPSET']._widget,
            self.compset_desc_widget],
                layout = {'border':'1px solid silver', 'overflow': 'hidden', 'height':'310px'}
        )

        vbx_grids = widgets.VBox([
            ConfigVar.vdict['GRID']._widget,
            self._btn_grid_view],
        layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'center'})
        vbx_grids.layout.border = '1px solid silver'
        vbx_grids.layout.width = '800px'

        vbx_create_case = widgets.VBox([
            self.scientific_only_widget,
            HeaderWidget("Compset:"),
            vbx_compset,
            HeaderWidget("Grid:"),
            vbx_grids,
            HeaderWidget("Launch:"),
            self._create_case
        ])

        return vbx_create_case
