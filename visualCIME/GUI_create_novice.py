import os, sys, re
import ipywidgets as widgets
import subprocess

from visualCIME.visualCIME.ConfigVar import ConfigVar
from visualCIME.visualCIME.OutHandler import handler as owh

import logging
logger = logging.getLogger(__name__)

class GUI_create_novice():

    def __init__(self, ci):
        self.ci = ci
        self._init_configvars()
        self._init_widgets()
        self._construct_all_widget_observances()

    def _init_configvars(self):

        for comp_class in self.ci.comp_classes:
            cv_comp_mode = ConfigVar('COMP_{}_MODE'.format(comp_class))

        cv_compset = ConfigVar('COMPSET')
        cv_grid = ConfigVar('GRID')
        cv_casename = ConfigVar('CASENAME')

    def _init_widgets(self):

        self.support_level_widget = widgets.ToggleButtons(
            options=['Defined', 'Tested', 'Scientific'],
            tooltips=['The component set is defined but has not been tested.',
                      'The defined component set has been tested with a scientifically supported grid resolution.',
                      'The tested component set has been validated scientifically.'],
            value='Defined',
            #layout={'width': 'max-content'}, # If the items' names are long
            description='Support Level:',
            disabled=True
        )
        self.support_level_widget.style.button_width='80px'
        self.support_level_widget.style.description_width = '140px'

        self.defined_by_widget = widgets.Dropdown(
            options=['all']+list(self.ci.compsets.keys()),
            value='all',
            description='Compsets defined by:',
        )
        self.defined_by_widget.style.description_width = '160px'

        self.comp_labels = []
        for comp_class in self.ci.comp_classes:
            self.comp_labels.append(
                widgets.Label(
                    value = '{} {} {}'.format(
                        chr(int("2000",base=16)), chr(int("25BC",base=16)), comp_class),
                    layout = widgets.Layout(width='110px',display='flex')
                )
            )

        for comp_class in self.ci.comp_classes:
            cv_comp_mode = ConfigVar.vdict['COMP_{}_MODE'.format(comp_class)]
            cv_comp_mode.widget = widgets.RadioButtons(
                options = ['all', 'active', 'data', 'stub'],
                description=comp_class,
                disabled=False,
                layout=widgets.Layout(width='110px', max_height='120px')
            )
            cv_comp_mode.widget.style.description_width = '0px'

        self.keywords_widget = widgets.Textarea(
            value = '',
            placeholder = 'Type keywords separated by comma',
            description = "Keywords:",
            disabled=False,
            layout=widgets.Layout(height='30px', width='500px')
        )

        self.search_widget = widgets.Button(
            description='Search',
            tooltip='Search within available compsets.',
            icon='search',
            layout = {'width':'100px'}
        )

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
            description='Defined compsets:',
            disabled=True,
            layout=widgets.Layout(width='650px')
        )
        cv_compset.widget.style.description_width = '120px'

        cv_grid = ConfigVar.vdict['GRID']
        cv_grid.widget = widgets.Combobox(
             options=[],
             placeholder = '(Finalize Compset First.)',
             description='Compatible Grids:',
             disabled=True,
             layout=widgets.Layout(width='650px')
        )
        cv_grid.widget.style.description_width = '120px'

        cv_casename = ConfigVar.vdict['CASENAME']
        cv_casename.widget = widgets.Textarea(
            value='',
            placeholder='Type case name',
            description='Case name:',
            disabled=True,
            layout=widgets.Layout(height='30px', width='400px')
        )
        cv_casename.widget.style.description_width = '120px'

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

        available_compsets = []
        if self.defined_by_widget.value == 'all':
            for component in self.ci.compsets:
                available_compsets += self.ci.compsets[component]
        else:
            available_compsets = self.ci.compsets[self.defined_by_widget.value]

        if self.keywords_widget.value != '':
            keywords = self.keywords_widget.value.split(',')
            new_available_compsets = []
            for ac in available_compsets:
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
            available_compsets = new_available_compsets

        available_compsets_str = ['{}: {}'.format(ac[0], ac[1]) for ac in available_compsets]

        cv_compset = ConfigVar.vdict['COMPSET']
        cv_compset.widget.options = available_compsets_str
        cv_compset.widget.placeholder = 'Select from {} available compsets'.format(len(cv_compset.widget.options))
        cv_compset.widget.disabled = False

    def _update_case_create(self, change):

        cv_casename = ConfigVar.vdict['CASENAME']
        cv_casename.widget.value = ""
        cv_casename.widget.disabled = True
        self.btn_create.disabled = True
        if change == None:
            return
        else:
            if change['old'] == {}:
                # Change in owner not finalized yet. Do nothing for now.
                return
            else:
                new_grid = change['old']['value']
                if new_grid and len(new_grid)>0:
                    cv_casename.widget.disabled = False
                    self.btn_create.disabled = False


    def _update_grid_widget(self, change):

        new_compset_lname = None
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
                new_compset_lname = new_compset.split(':')[1].strip()

        cv_grid = ConfigVar.vdict['GRID']
        if new_compset_lname==None:
            cv_grid.widget.disabled = True
            cv_grid.widget.placeholder = '(Finalize Compset First.)'
        else:
            compatible_grids = []
            for alias, compset_attr, not_compset_attr in self.ci.model_grids:
                if compset_attr and not re.search(compset_attr, new_compset_lname):
                    continue
                if not_compset_attr and re.search(not_compset_attr, new_compset_lname):
                    continue
                compatible_grids.append(alias)

            if len(compatible_grids)==0:
                cv_grid.widget.disabled = True
                cv_grid.widget.placeholder = 'No compatible grids. Change COMPSET.'
            else:
                cv_grid.widget.disabled = False
                cv_grid.widget.placeholder = 'Select from {} compatible grids'.format(len(compatible_grids))
                cv_grid.widget.value = ''
                cv_grid.widget.options = compatible_grids


    def _create_case(self, b):

        cv_grid = ConfigVar.vdict["GRID"]
        cv_casename = ConfigVar.vdict["CASENAME"]
        cv_compset = ConfigVar.vdict['COMPSET']
        compset_alias = cv_compset.widget.value.split(':')[0]
        self.create_case_out.clear_output()
        with self.create_case_out:
            cmd = "{}/scripts/create_newcase --res {} --compset {} --case {} --run-unsupported".format(
                self.ci.cimeroot,
                cv_grid.widget.value,
                compset_alias,
                cv_casename.widget.value)
            print("Running cmd: {}".format(cmd))
            runout = subprocess.run(cmd, shell=True, capture_output=True)
            if runout.returncode == 0:
                print("".format(runout.stdout))
                print("SUCCESS: case created at {} ".format(cv_casename.widget.value))
            else:
                print(runout.stdout)
                print("ERROR: {} ".format(runout.stderr))

    def _construct_all_widget_observances(self):

        self.search_widget.on_click(self._update_compsets)

        cv_compset = ConfigVar.vdict['COMPSET']
        cv_compset.widget.observe(
            self._update_grid_widget,
            names='_property_lock',
            type='change'
        )

        cv_grid = ConfigVar.vdict['GRID']
        cv_grid.widget.observe(
            self._update_case_create,
            names='_property_lock',
            type='change'
        )

        self.btn_create.on_click(self._create_case)

    def construct(self):

        hbx_comp_labels = widgets.HBox(self.comp_labels)
        hbx_comp_modes = widgets.HBox([ConfigVar.vdict['COMP_{}_MODE'.format(comp_class)].widget for comp_class in self.ci.comp_classes])
        vbx_create_case = widgets.VBox([
            self.support_level_widget,
            widgets.Label(''),
            self.defined_by_widget,
            widgets.Label(''),
            hbx_comp_labels,
            hbx_comp_modes,
            self.keywords_widget,
            widgets.VBox([
                widgets.Label(''),
                widgets.HBox([self.search_widget])],
                layout={'align_items':'flex-end'}),
            ConfigVar.vdict['COMPSET'].widget,
            ConfigVar.vdict['GRID'].widget,
            ConfigVar.vdict['CASENAME'].widget,
            widgets.VBox([
                widgets.Label(''),
                widgets.HBox([self.btn_create])],
                layout={'align_items':'flex-end'}),
            self.create_case_out
        ])

        return vbx_create_case
