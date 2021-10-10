import os, sys, re
import ipywidgets as widgets
import subprocess

from visualCaseGen.visualCaseGen.ConfigVar import ConfigVar
from visualCaseGen.visualCaseGen.ConfigVarOpt import ConfigVarOpt
from visualCaseGen.visualCaseGen.OutHandler import handler as owh

import logging
logger = logging.getLogger(__name__)

class GUI_create_predefined():

    def __init__(self, ci):
        self.ci = ci
        self._init_configvars()
        self._init_widgets()
        self._construct_all_widget_observances()
        self._update_compsets(None)
        self._available_compsets = []

    def _init_configvars(self):

        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVarOpt('COMP_{}'.format(comp_class))

        cv_compset = ConfigVarOpt('COMPSET', NoneVal='')
        cv_grid = ConfigVarOpt('GRID', NoneVal='')
        cv_casename = ConfigVar('CASENAME')

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
                    layout = widgets.Layout(width='100px',display='flex',justify_content='center')
                )
            )

        for comp_class in self.ci.comp_classes:
            cv_comp_models = ['any']
            for model in self.ci.models[comp_class]:
                if model[0]=='x':
                    logger.debug("Skipping the dead component {}.".format(model))
                    continue
                elif model.upper() == 'D'+comp_class.strip() or model.upper() == 'S'+comp_class:
                    continue # will add to end
                if model not in cv_comp_models:
                    cv_comp_models.append(model)
            cv_comp_models += ['data', 'none']

            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.widget = widgets.ToggleButtons(
                options = cv_comp_models,
                description=comp_class,
                disabled=False,
                layout=widgets.Layout(width='105px', max_height='120px')
            )
            cv_comp.widget_style.button_width = '85px'
            cv_comp.widget_style.description_width = '0px'

        self.keywords_widget = widgets.Textarea(
            value = '',
            placeholder = 'Type keywords to filter compsets below',
            description = "Keywords:",
            disabled=False,
            layout=widgets.Layout(height='30px', width='500px', description_width='120px', padding='10px')
        )
        self.keywords_widget.style.description_width = '90px'

        self.reset_widget = widgets.Button(
            description='Reset',
            disabled=True,
            button_style='danger', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Reset',
            icon='undo',
            layout = {'width':'100px'},
        )

        cv_compset = ConfigVar.vdict['COMPSET']
        cv_compset.widget = widgets.Combobox(
            options=[],
            placeholder = '(Hit Search button)',
            description='Compset:',
            disabled=True,
            layout=widgets.Layout(width='650px', padding='10px')
        )
        cv_compset.widget_style.description_width = '90px'

        cv_grid = ConfigVar.vdict['GRID']
        cv_grid.widget = widgets.Combobox(
             options=[],
             placeholder = '(Finalize Compset First.)',
             description='Compatible Grids:',
             disabled=True,
             layout=widgets.Layout(width='650px')
        )
        cv_grid.widget_style.description_width = '120px'

        cv_casename = ConfigVar.vdict['CASENAME']
        cv_casename.widget = widgets.Textarea(
            value='',
            placeholder='Type case name',
            description='Case name:',
            disabled=True,
            layout=widgets.Layout(height='30px', width='500px')
        )
        cv_casename.widget_style.description_width = '120px'

        self.drp_machines = widgets.Dropdown(
            options=self.ci.machines,
            value=self.ci.machine,
            layout={'width': 'max-content'}, # If the items' names are long
            description='Machine name',
            disabled= (self.ci.machine != None)
        )
        self.drp_machines.style.description_width = '120px'

        self.btn_create = widgets.Button(
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

    def _update_compsets(self, b):

        # First, reset both the compset and the grid widgets:
        cv_compset = ConfigVar.vdict['COMPSET']
        cv_compset.value = ''
        self._reset_grid_widget()

        # Now, determine all available compsets
        self._available_compsets = []

        if self.scientific_only_widget.value == True:
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
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            filter_compsets.append((comp_class,cv_comp.value))


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
        cv_compset.set_widget_properties({
            'placeholder': 'Select from {} available compsets'.format(len(cv_compset.options)),
            'disabled': False })

    def _reset_case_create(self):
        cv_casename = ConfigVar.vdict['CASENAME']
        cv_casename.value = ""
        cv_casename.set_widget_properties({'disabled':True})
        self.btn_create.disabled = True

    def _update_case_create(self, change):

        self._reset_case_create()
        if change == None:
            return
        else:
            if change['old'] == {}:
                # Change in owner not finalized yet. Do nothing for now.
                return
            else:
                if self.drp_machines.value:
                    new_grid = change['old']['value']
                    if new_grid and len(new_grid)>0:
                        cv_casename = ConfigVar.vdict['CASENAME']
                        cv_casename.set_widget_properties({'disabled':False})
                        self.btn_create.disabled = False

    def _call_update_case_create(self, change):
        cv_grid = ConfigVar.vdict['GRID']
        if cv_grid.get_widget_property('disabled') == True:
            return
        if change == None:
            return
        else:
            if change['old'] == {}:
                # Change in owner not finalized yet. Do nothing for now.
                return
            else:
                self._update_case_create({'old':{'value':cv_grid.value}})


    def _reset_grid_widget(self):
        cv_grid = ConfigVar.vdict['GRID']
        cv_grid.value = ''
        cv_grid.options = []
        cv_grid.set_widget_properties({
            'placeholder': '(Finalize Compset First.)',
            'disabled': True
        })
        self._reset_case_create()

    def _update_grid_widget(self, change):

        if change == None:
            return
        else:
            if change['old'] == {}:
                # Change in owner not finalized yet. Do nothing for now.
                return
            else:
                new_compset = change['old']['value']
                if len(new_compset)==0 or ':' not in new_compset:
                    return

        new_compset_alias = new_compset.split(':')[0].strip()
        new_compset_lname = new_compset.split(':')[1].strip()

        cv_grid = ConfigVar.vdict['GRID']
        compatible_grids = []
        if self.scientific_only_widget.value == True:
            for alias, lname, sci_supported_grid in self._available_compsets:
                if new_compset_alias == alias:
                    compatible_grids = sci_supported_grid
                    break
        else:
            for alias, compset_attr, not_compset_attr, desc in self.ci.model_grids:
                if compset_attr and not re.search(compset_attr, new_compset_lname):
                    continue
                if not_compset_attr and re.search(not_compset_attr, new_compset_lname):
                    continue
                compatible_grids.append(alias)

        if len(compatible_grids)==0:
            cv_grid.set_widget_properties({
                'placeholder': 'No compatible grids. Change COMPSET.',
                'disabled': True
            })
        else:
            ngrids = len(compatible_grids)
            cv_grid.set_widget_properties({
                'placeholder': 'Select from {} compatible grids'.format(ngrids),
                'disabled': False
            })
            cv_grid.options = compatible_grids
            if ngrids==1:
                cv_grid.value = compatible_grids[0]
                self._update_case_create({'old':{'value':cv_grid.value}})
            else:
                cv_grid.value = ''


    def _create_case(self, b):

        cv_grid = ConfigVar.vdict["GRID"]
        cv_casename = ConfigVar.vdict["CASENAME"]
        cv_compset = ConfigVar.vdict['COMPSET']
        compset_alias = cv_compset.value.split(':')[0]
        self.create_case_out.clear_output()
        with self.create_case_out:
            cmd = "{}/scripts/create_newcase --res {} --compset {} --case {} --machine {} --run-unsupported".format(
                self.ci.cimeroot,
                cv_grid.value,
                compset_alias,
                cv_casename.value,
                self.drp_machines.value)
            print("Running cmd: {}".format(cmd))
            runout = subprocess.run(cmd, shell=True, capture_output=True)
            if runout.returncode == 0:
                print("".format(runout.stdout))
                print("SUCCESS: case created at {} ".format(cv_casename.value))
            else:
                print(runout.stdout)
                print("ERROR: {} ".format(runout.stderr))

    def _construct_all_widget_observances(self):

        self.scientific_only_widget.observe(
            self._update_compsets,
            names='value'
        )

        cv_compset = ConfigVar.vdict['COMPSET']
        cv_compset.observe(
            self._update_grid_widget,
            names='_property_lock',
            type='change'
        )

        cv_grid = ConfigVar.vdict['GRID']
        cv_grid.observe(
            self._update_case_create,
            names='_property_lock',
            type='change'
        )

        self.btn_create.on_click(self._create_case)

        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.observe(
                self._update_compsets,
                names='_property_lock',
                type='change'
            )

        self.keywords_widget.observe(
            self._update_compsets,
            names='_property_lock',
            type='change'
        )

        self.drp_machines.observe(
            self._call_update_case_create,
            names='_property_lock',
            type='change'
        )

    def construct(self):

        hbx_comp_labels = widgets.HBox(self.comp_labels)
        hbx_comp_modes = widgets.HBox([ConfigVar.vdict['COMP_{}'.format(comp_class)]._widget for comp_class in self.ci.comp_classes])
        hbx_comp_modes.layout.width = '800px'
        hbx_comp_modes.layout.height = '170px'

        vbx_compset = widgets.VBox([
            hbx_comp_labels,
            hbx_comp_modes,
            self.keywords_widget,
            ConfigVar.vdict['COMPSET']._widget,
        ])
        vbx_compset.layout.border = '1px solid silver'

        vbx_grid = widgets.VBox([
            ConfigVar.vdict['GRID']._widget,
        ])
        vbx_grid.layout.border = '1px solid silver'

        vbx_create_case = widgets.VBox([
            self.scientific_only_widget,
            widgets.Label(value="Select a Compset:"),
            vbx_compset,
            widgets.Label(value="Select a Grid:"),
            vbx_grid,
            widgets.Label(''),
            self.drp_machines,
            widgets.HBox([
                ConfigVar.vdict['CASENAME']._widget,
                widgets.HBox([self.btn_create])],
                layout={'align_items':'flex-end'}),
            self.create_case_out
        ])

        return vbx_create_case
