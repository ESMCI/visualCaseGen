import os, sys, re
import ipywidgets as widgets

from visualCIME.visualCIME.ConfigVar import ConfigVar
from visualCIME.visualCIME.OutHandler import handler as owh

import logging
logger = logging.getLogger(__name__)

class GUI_create_advanced():

    def __init__(self, ci):
        self.ci = ci
        self.init_configvars()
        self.init_configvar_widgets()
        self.construct_all_widget_observances()

    def init_configvars(self):
        """ Initialize the ConfigVar instances to be displayed on the GUI as configurable case variables.
        """
        logger.debug("Initializing ConfigVars...")

        # Create Case
        cv_inittime = ConfigVar('INITTIME')
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar('COMP_'+str(comp_class))
            cv_comp_phys = ConfigVar('COMP_{}_PHYS'.format(comp_class))
            cv_comp_option = ConfigVar('COMP_{}_OPTION'.format(comp_class))
        cv_compset = ConfigVar('COMPSET')

    def init_configvar_widgets(self):
        # Create Case: --------------------------------------

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
            cv_comp.widget.style.description_width = '1px'

            # COMP_{}_PHYS widget
            cv_comp_phys.widget = widgets.ToggleButtons(
                    options=[],
                    value=None,
                    description=comp_class+':',
                    disabled=False,
                    layout=widgets.Layout(width='110px', max_height='100px')
                )
            cv_comp_phys.widget.style.button_width = '90px'
            cv_comp_phys.widget.style.description_width = '1px'

            # COMP_{}_OPTION widget
            cv_comp_option.widget = widgets.ToggleButtons(
                    options=[],
                    value=None,
                    description=comp_class+':',
                    disabled=False,
                    layout=widgets.Layout(width='110px', max_height='100px')
                )
            cv_comp_option.widget.style.button_width = '90px'
            cv_comp_option.widget.style.description_width = '1px'

        cv_compset = ConfigVar.vdict['COMPSET']
        cv_compset.widget = widgets.HTML(value = f"<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>")


    @owh.out.capture()
    def update_comp_phys_and_options(self,change=None):
        if change != None:
            new_val = change['owner'].value
            comp_class = change['owner'].description[0:3]
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            assert re.search("COMP_...", cv_comp.name)
            if (not ConfigVar.value_is_valid(new_val)) or change['old'] == {}:
                logger.debug("No need to update comp physics and options for {}".format(cv_comp.name))
                return

            logger.debug("Updating the physics and options of ConfigVar {} with value={}".format(cv_comp.name, cv_comp.widget.value))
            comp_phys, comp_options, comp_phys_desc, comp_options_desc = [], [], [], []
            if cv_comp.widget.value != None:
                model = ConfigVar.strip_option_status(cv_comp.widget.value)
                comp_phys, comp_options, comp_phys_desc, comp_options_desc = self.ci.phys_opt[model]

            if len(comp_phys)==0 and cv_comp.widget.value != None:
                comp_phys = [cv_comp.widget.value.upper()]
                comp_phys_desc = comp_phys
            comp_options = ['(none)'] + comp_options
            comp_options_desc = ['(none)'] + comp_options_desc

            cv_comp_phys = ConfigVar.vdict["COMP_{}_PHYS".format(comp_class)]
            cv_comp_phys.update_states(change=None, new_options=comp_phys, tooltips=comp_phys_desc)

            cv_comp_option = ConfigVar.vdict["COMP_{}_OPTION".format(comp_class)]
            cv_comp_option.update_states(change=None, new_options=comp_options, tooltips=comp_options_desc)
        else:
            raise NotImplementedError

    @owh.out.capture()
    def update_compset(self,change=None):
        cv_compset = ConfigVar.vdict['COMPSET']
        compset_text = ConfigVar.vdict['INITTIME'].get_value()
        for comp_class in self.ci.comp_classes:
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
            comp_phys_val = cv_comp_phys.get_value()
            comp_option_val = cv_comp_option.get_value()
            if comp_phys_val != None:
                compset_text += '_'+comp_phys_val
                if comp_option_val != None and comp_option_val != '(none)':
                    compset_text += '%'+comp_option_val
            else:
                cv_compset.widget.value = f"<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>"
                return
        cv_compset.widget.value = compset_text
        cv_compset.widget.value = f"<p style='text-align:right'><b><i>compset: </i><font color='green'>{compset_text}</b></p>"


    def construct_all_widget_observances(self):

        # Assign the compliances property of all ConfigVar instsances:
        ConfigVar.compliances = self.ci.compliances

        # Build validity observances:
        for varname, var in ConfigVar.vdict.items():
            var.observe_value_validity()

        # Build relational observances:
        for varname, var in ConfigVar.vdict.items():
            var.observe_relations()

        # Update COMP_{} states
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.update_states()

        # Build options observances for comp_phys and comp_option
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.widget.observe(
                self.update_comp_phys_and_options,
                names='_property_lock',
                type='change')

        cv_inittime = ConfigVar.vdict['INITTIME']
        cv_inittime.widget.observe(
            self.update_compset,
            names='_property_lock',
            type='change'
        )
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.widget.observe(
                self.update_compset,
                names='_property_lock',
                type='change')
            cv_comp_phys = ConfigVar.vdict['COMP_{}_PHYS'.format(comp_class)]
            cv_comp_phys.widget.observe(
                self.update_compset,
                names='_property_lock',
                type='change')
            cv_comp_option = ConfigVar.vdict['COMP_{}_OPTION'.format(comp_class)]
            cv_comp_option.widget.observe(
                self.update_compset,
                names='_property_lock',
                type='change')

    def construct(self):

        def _constr_hbx_components():
            hbx_components = widgets.HBox([ConfigVar.vdict['COMP_{}'.format(comp_class)].widget for comp_class in self.ci.comp_classes])
            hbx_components.layout.border = '2px dotted lightgray'
            hbx_components.layout.width = '850px'
            return hbx_components

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
            hbx_grids = widgets.HBox([widgets.Label(value="Grids options will be displayed here.")])
            hbx_grids.layout.border = '2px dotted lightgray'
            return hbx_grids


        def _constr_hbx_case():
            #Case Name
            txt_casename = widgets.Textarea(
                value='',
                placeholder='Type case name',
                description='Case name:',
                disabled=False,
                layout=widgets.Layout(height='30px', width='400px')
            )

            #Create Case:
            btn_create = widgets.Button(
                value=False,
                description='Create new case',
                disabled=False,
                button_style='', # 'success', 'info', 'warning', 'danger' or ''
                tooltip='Description',
                icon='check',
                layout=widgets.Layout(height='30px')
            )
            btn_setup = widgets.Button(
                value=False,
                description='setup',
                disabled=False,
                button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
                tooltip='Description',
                layout=widgets.Layout(height='30px', width='80px')
            )
            btn_build = widgets.Button(
                value=False,
                description='build',
                disabled=False,
                button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
                tooltip='Description',
                layout=widgets.Layout(height='30px', width='80px')
            )
            btn_submit = widgets.Button(
                value=False,
                description='submit',
                disabled=False,
                button_style='warning', # 'success', 'info', 'warning', 'danger' or ''
                tooltip='Description',
                layout=widgets.Layout(height='30px', width='80px')
            )
            #Component options:
            hbx_case = widgets.HBox([txt_casename, btn_create, btn_setup, btn_build, btn_submit])
            return hbx_case
        ## END -- functions to determine the GUI layout

        vbx_create_case = widgets.VBox([
            ConfigVar.vdict['INITTIME'].widget,
            widgets.Label(value="Components:"),
            _constr_hbx_components(),
            widgets.Label(value="Component Physics:"),
            _constr_hbx_comp_phys(),                                
            widgets.Label(value="Component Options:"),
            _constr_hbx_comp_options(),
            ConfigVar.vdict['COMPSET'].widget,
            widgets.Label(value="Grids:"),
            _constr_hbx_grids(),
            widgets.Label(value=""),
            _constr_hbx_case()
        ])

        return vbx_create_case
