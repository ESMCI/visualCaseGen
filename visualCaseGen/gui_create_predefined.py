import re
import logging
import ipywidgets as widgets

#todo from visualCaseGen.config_var import ConfigVar
#todo from visualCaseGen.config_var_opt import ConfigVarOpt
#todo from visualCaseGen.config_var_opt_ms import ConfigVarOptMS
#todo from visualCaseGen.checkbox_multi_widget import CheckboxMultiWidget
#todo from visualCaseGen.create_case_widget import CreateCaseWidget
#todo from visualCaseGen.header_widget import HeaderWidget

logger = logging.getLogger(__name__)

class GUI_create_predefined():

    def __init__(self, ci):
        self.ci = ci
        self._init_configvars()
        self._init_widgets()
        self._construct_all_widget_observances()
        self._update_compsets(None)
        self._available_compsets = []
        self._grid_view_mode = 'suggested' # or 'all'

    def _init_configvars(self):

        pass
        #todo for comp_class in self.ci.comp_classes:
        #todo     ConfigVarOpt('COMP_{}'.format(comp_class))

        #todo ConfigVarOpt('COMPSET', none_val=None)
        #todo ConfigVarOptMS('GRID')

    def _init_widgets(self):

        pass
        #todo self.scientific_only_widget = widgets.Checkbox(
        #todo     value=False,
        #todo     #layout={'width': 'max-content'}, # If the items' names are long
        #todo     description='Scientifically supported configs only',
        #todo     disabled=False,
        #todo     layout=widgets.Layout(left='-40px', margin='10px', width='500px')
        #todo )

        #todo self.comp_labels = []
        #todo for comp_class in self.ci.comp_classes:
        #todo     self.comp_labels.append(
        #todo         widgets.Label(
        #todo             value = '{} {} {}'.format(
        #todo                 chr(int("2000",base=16)), chr(int("25BC",base=16)), comp_class),
        #todo             layout = widgets.Layout(width='105px',display='flex',justify_content='center')
        #todo         )
        #todo     )

        #todo for comp_class in self.ci.comp_classes:
        #todo     cv_comp_models = ['any']
        #todo     for model in self.ci.models[comp_class]:
        #todo         if model[0]=='x':
        #todo             logger.debug("Skipping the dead component %s", model)
        #todo             continue
        #todo         if model.upper() == 'D'+comp_class.strip() or model.upper() == 'S'+comp_class:
        #todo             continue # will add to end
        #todo         if model not in cv_comp_models:
        #todo             cv_comp_models.append(model)
        #todo     cv_comp_models += ['data', 'none']

        #todo     cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
        #todo     cv_comp.widget = widgets.ToggleButtons(
        #todo         options = cv_comp_models,
        #todo         description=comp_class,
        #todo         disabled=False,
        #todo         layout=widgets.Layout(width='105px', max_height='120px')
        #todo     )
        #todo     cv_comp.widget_style.button_width = '85px'
        #todo     cv_comp.widget_style.description_width = '0px'

        #todo self.keywords_widget = widgets.Textarea(
        #todo     value = '',
        #todo     placeholder = 'Type keywords to filter compsets below',
        #todo     description = "Keywords:",
        #todo     disabled=False,
        #todo     layout=widgets.Layout(height='30px', width='500px', description_width='120px', padding='10px')
        #todo )
        #todo self.keywords_widget.style.description_width = '90px'

        #todo cv_compset = ConfigVar.vdict['COMPSET']
        #todo cv_compset.widget = widgets.Dropdown(
        #todo     options=[],
        #todo     description='Compset:',
        #todo     disabled=True,
        #todo     ensure_option=True,
        #todo     layout=widgets.Layout(width='650px', padding='10px')
        #todo )
        #todo cv_compset.widget_style.description_width = '90px'
        #todo cv_compset.valid_opt_icon = chr(int('27A4',base=16))

        #todo self.compset_desc_widget = widgets.Label("", layout = {'left':'160px', 'margin':'10px'})

        #todo cv_grid = ConfigVar.vdict['GRID']
        #todo cv_grid.widget = CheckboxMultiWidget(
        #todo      options=[],
        #todo      placeholder = '(Finalize Compset First.)',
        #todo      description='Compatible Grids:',
        #todo      disabled=True,
        #todo      allow_multi_select=False,
        #todo      #todo layout=widgets.Layout(width='500px')
        #todo )
        #todo cv_grid.valid_opt_icon = chr(int('27A4',base=16))

        #todo self._btn_grid_view = widgets.Button(
        #todo     description='show all grids',
        #todo     icon='chevron-down',
        #todo     layout = {'display':'none', 'width':'200px', 'margin':'10px'}
        #todo )

        #todo self._create_case = CreateCaseWidget(
        #todo     self.ci,
        #todo     layout=widgets.Layout(width='800px', border='1px solid silver', padding='10px')
        #todo )

    def _update_compsets(self, b):

        pass
        #todo # First, reset both the compset and the grid widgets:
        #todo cv_compset = ConfigVar.vdict['COMPSET']
        #todo self._reset_grid_widget()

        #todo # Now, determine all available compsets
        #todo self._available_compsets = []

        #todo if self.scientific_only_widget.value is True:
        #todo     # add scientifically supported compsets only
        #todo     for component in self.ci.compsets:
        #todo         for compset in self.ci.compsets[component]:
        #todo             if len(compset.sci_supported_grids)>0:
        #todo                 self._available_compsets.append(compset)
        #todo else:
        #todo     # add all compsets regardless of support level
        #todo     for component in self.ci.compsets:
        #todo         self._available_compsets += self.ci.compsets[component]

        #todo filter_compsets = []
        #todo for comp_class in self.ci.comp_classes:
        #todo     cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
        #todo     filter_compsets.append((comp_class,cv_comp.value))


        #todo new_available_compsets = []
        #todo for compset in self._available_compsets:
        #todo     filter_compset = False
        #todo     for comp_class, model in filter_compsets:
        #todo         if model == "any":
        #todo             pass
        #todo         elif (model == "none" and 'S'+comp_class not in compset.lname) or\
        #todo              (model == "data" and 'D'+comp_class not in compset.lname) or\
        #todo              (model not in ["none", "data"] and model.upper() not in compset.lname):
        #todo             filter_compset = True
        #todo             break

        #todo     if not filter_compset:
        #todo         new_available_compsets.append(compset)
        #todo self._available_compsets = new_available_compsets


        #todo if self.keywords_widget.value != '':
        #todo     keywords = self.keywords_widget.value.split(',')
        #todo     new_available_compsets = []
        #todo     for ac in self._available_compsets:
        #todo         all_keywords_found = True
        #todo         for keyword in keywords:
        #todo             keyword = keyword.strip()
        #todo             if keyword in ac[1] or keyword in ac[0]:
        #todo                 pass
        #todo             else:
        #todo                 all_keywords_found = False
        #todo                 break
        #todo         if all_keywords_found:
        #todo             new_available_compsets.append(ac)
        #todo     self._available_compsets = new_available_compsets

        #todo available_compsets_str = ['{}: {}'.format(ac.alias, ac.lname) for ac in self._available_compsets]

        #todo cv_compset.options = available_compsets_str
        #todo cv_compset.set_widget_properties({'disabled': False })
        #todo n_available_compsets = len(cv_compset.options)
        #todo if n_available_compsets > 0:
        #todo     self.compset_desc_widget.value = '{} Select from {} available compsets above.'.\
        #todo         format(chr(int("2191",base=16)), n_available_compsets)
        #todo else:
        #todo     self.compset_desc_widget.value = '{} Cannot find any compsets with the above filters/keywords.'.\
        #todo         format(chr(int("2757",base=16)))

    def _reset_grid_widget(self):

        pass
        #todo cv_grid = ConfigVar.vdict['GRID']
        #todo cv_grid.value = ()
        #todo cv_grid.options = []
        #todo cv_grid.set_widget_properties({
        #todo     'placeholder': '(Finalize Compset First.)',
        #todo     'disabled': True
        #todo })
        #todo self._btn_grid_view.layout.display = 'none'
        #todo self._create_case.disable()

    def _update_grid_widget(self, change):

        pass
        #todo if change is None:
        #todo     return

        #todo new_compset = ''
        #todo if 'old' in change: # invoked by user frontend change
        #todo     if change['old'] == {}:
        #todo         # Change in owner not finalized yet. Do nothing for now.
        #todo         return
        #todo     new_compset = change['old']['value']
        #todo else: # invoked by backend
        #todo     new_compset = ConfigVar.vdict['COMPSET'].value

        #todo if new_compset is None:
        #todo     return
        #todo if len(new_compset)==0 or ':' not in new_compset:
        #todo     return

        #todo self.compset_desc_widget.value = "" # a valid compset selection made. reset compset_desc_widget

        #todo new_compset_alias = new_compset.split(':')[0].strip()
        #todo new_compset_lname = new_compset.split(':')[1].strip()

        #todo cv_grid = ConfigVar.vdict['GRID']
        #todo compatible_grids = []
        #todo grid_descriptions = []
        #todo if self.scientific_only_widget.value is True:
        #todo     for alias, lname, sci_supported_grids in self._available_compsets:
        #todo         if new_compset_alias == alias:
        #todo             compatible_grids = sci_supported_grids
        #todo             grid_descriptions = ['scientifically supported grid for {}'.format(alias)]*len(compatible_grids)
        #todo             break
        #todo else:
        #todo     for alias, compset_attr, not_compset_attr, desc in self.ci.model_grids:
        #todo         if compset_attr and not re.search(compset_attr, new_compset_lname):
        #todo             continue
        #todo         if not_compset_attr and re.search(not_compset_attr, new_compset_lname):
        #todo             continue
        #todo         if self._grid_view_mode == 'suggested' and desc == '':
        #todo             continue
        #todo         compatible_grids.append(alias)
        #todo         grid_descriptions.append(desc)

        #todo if len(compatible_grids)==0:
        #todo     cv_grid.set_widget_properties({'disabled': True})
        #todo     if self._grid_view_mode == 'suggested':
        #todo         cv_grid.set_widget_properties({
        #todo             'placeholder': "Couldn't find any suggested grids. Show all grids or change COMPSET."})
        #todo     else:
        #todo         cv_grid.set_widget_properties({
        #todo             'placeholder': 'No compatible grids. Change COMPSET.'})
        #todo else:
        #todo     cv_grid.set_widget_properties({
        #todo         'disabled': False,
        #todo         'placeholder': 'Select from {} compatible grids'.format(len(compatible_grids)),
        #todo     })
        #todo     cv_grid.value = ()
        #todo     cv_grid.options = compatible_grids
        #todo     cv_grid.tooltips = grid_descriptions

        #todo     if self.scientific_only_widget.value is True:
        #todo         self._btn_grid_view.layout.display = 'none' # turn off the display
        #todo     else:
        #todo         self._btn_grid_view.layout.display = '' # turn on the display

    def _refresh_grids_list_wrapper(self, change):

        pass
        #todo if self.scientific_only_widget is True:
        #todo     self._refresh_grids_list(new_mode='all')
        #todo else:
        #todo     self._refresh_grids_list(new_mode='suggested')

    def _refresh_grids_list(self, change=None, new_mode=None):

        pass
        #todo # first, update the grid_view_mode attribute
        #todo if new_mode:
        #todo     # invoked by backend
        #todo     self._grid_view_mode = new_mode
        #todo else:
        #todo     # invoked by frontend click
        #todo     if self._grid_view_mode == 'all':
        #todo         self._grid_view_mode = 'suggested'
        #todo     else:
        #todo         self._grid_view_mode = 'all'
        #todo self._btn_grid_view.icon = 'hourglass-start'
        #todo self._btn_grid_view.description = ''

        #todo # second, update the grid list accordingly
        #todo self._update_grid_widget({})

        #todo # finally, update the grid view mode button
        #todo if self._grid_view_mode == 'all':
        #todo     self._btn_grid_view.description = 'show suggested grids'
        #todo     self._btn_grid_view.icon = 'chevron-up'
        #todo else:
        #todo     self._btn_grid_view.description = 'show all grids'
        #todo     self._btn_grid_view.icon = 'chevron-down'

    def _update_create_case(self, change):

        pass
        #todo assert change['name'] == 'value'
        #todo self._create_case.disable()
        #todo new_grid = change['new']
        #todo if new_grid and len(new_grid)>0:
        #todo     compset_text = ConfigVar.vdict['COMPSET'].value.split(':')[0]
        #todo     self._create_case.enable(compset_text, new_grid[0][1:].strip())

    def _construct_all_widget_observances(self):

        pass
        #todo self.scientific_only_widget.observe(
        #todo     self._update_compsets,
        #todo     names='value'
        #todo )

        #todo cv_compset = ConfigVar.vdict['COMPSET']
        #todo cv_compset.observe(
        #todo     self._refresh_grids_list_wrapper,
        #todo     names='_property_lock',
        #todo     type='change'
        #todo )

        #todo cv_grid = ConfigVar.vdict['GRID']
        #todo cv_grid.observe(
        #todo     self._update_create_case,
        #todo     names='value',
        #todo     type='change'
        #todo )

        #todo for comp_class in self.ci.comp_classes:
        #todo     cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
        #todo     cv_comp.observe(
        #todo         self._update_compsets,
        #todo         names='_property_lock',
        #todo         type='change'
        #todo     )

        #todo self.keywords_widget.observe(
        #todo     self._update_compsets,
        #todo     names='_property_lock',
        #todo     type='change'
        #todo )

        #todo self._btn_grid_view.on_click(self._refresh_grids_list)

    def construct(self):

        #todo hbx_comp_labels = widgets.HBox(self.comp_labels)
        #todo hbx_comp_modes = widgets.HBox([ConfigVar.vdict['COMP_{}'.format(comp_class)]._widget\
        #todo      for comp_class in self.ci.comp_classes], layout={'overflow':'hidden'})
        #todo hbx_comp_modes.layout.width = '800px'

        #todo vbx_compset = widgets.VBox([
        #todo     hbx_comp_labels,
        #todo     hbx_comp_modes,
        #todo     self.keywords_widget,
        #todo     ConfigVar.vdict['COMPSET']._widget,
        #todo     self.compset_desc_widget],
        #todo         layout = {'border':'1px solid silver', 'overflow': 'hidden', 'height':'310px'}
        #todo )

        #todo vbx_grids = widgets.VBox([
        #todo     ConfigVar.vdict['GRID']._widget,
        #todo     self._btn_grid_view],
        #todo layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'center'})
        #todo vbx_grids.layout.border = '1px solid silver'
        #todo vbx_grids.layout.width = '800px'

        vbx_create_case = widgets.VBox([
        #todo     self.scientific_only_widget,
        #todo     HeaderWidget("Compset:"),
        #todo     vbx_compset,
        #todo     HeaderWidget("Grid:"),
        #todo     vbx_grids,
        #todo     HeaderWidget("Launch:"),
        #todo     self._create_case
        ])

        return vbx_create_case
