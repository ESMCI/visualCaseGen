import re

class OptionsSetter:
    def __init__(self, var, func, inducing_vars=[]):

        self.var = var
        self._func = func
        assert isinstance(inducing_vars, list), "incuding_vars parameter must be a list"
        self._inducing_vars = inducing_vars
        self.var.assign_options_setter(self)

    def __call__(self):

        if any([inducing_var.is_none() for inducing_var in self._inducing_vars]):
            return None, None

        options, tooltips = self._func(*(var.value for var in self._inducing_vars))
        return options, tooltips
    
    def has_inducing_vars(self):
        return len(self._inducing_vars)>0

    @property
    def inducing_vars(self):
        return self._inducing_vars


def get_options_setters(cvars, ci):

    options_setters = [] 

    INITTIME = cvars['INITTIME']
    options_setters.append(
        OptionsSetter(
            var = INITTIME, 
            func = lambda:(
                ['1850', '2000', 'HIST'],
                ['Pre-industrial', 'Present day', 'Historical'])
        )
    )

    for comp_class in ci.comp_classes:
        COMP = cvars['COMP_{}'.format(comp_class)]
        options_setters.append(
            OptionsSetter(
                var = COMP,
                func = lambda cc=comp_class:(
                    [model for model in ci.models[cc] if model[0] != 'x'],
                    None)
            )
        )

    for comp_class in ci.comp_classes:
        COMP = cvars['COMP_{}'.format(comp_class)]
        COMP_PHYS = cvars["COMP_{}_PHYS".format(comp_class)]
        options_setters.append(
            OptionsSetter(
                var = COMP_PHYS,
                func = lambda model:(
                    ci.comp_phys[model],
                    ci.comp_phys_desc[model]),
                inducing_vars = [COMP]
            )
        )

    for comp_class in ci.comp_classes:
        COMP = cvars['COMP_{}'.format(comp_class)]
        COMP_PHYS = cvars["COMP_{}_PHYS".format(comp_class)]
        COMP_OPTION = cvars["COMP_{}_OPTION".format(comp_class)]
        options_setters.append(
            OptionsSetter(
                var = COMP_OPTION,
                func = lambda model,phys:(
                    ['(none)']+ci.comp_options[model][phys],
                    ['no modifiers']+ci.comp_options_desc[model][phys]),
                inducing_vars = [COMP, COMP_PHYS],
            )
        )
    

    def compset_func(*args):

        new_compset_text = cvars['INITTIME'].value

        for comp_class in ci.comp_classes:

            # Component Physics:
            cv_comp_phys = cvars['COMP_{}_PHYS'.format(comp_class)]
            if cv_comp_phys.is_none():
                return [''] # not all component physics selected yet, so not ready to set COMPSET
            
            comp_phys_val = cv_comp_phys.value
            if comp_phys_val == "Specialized":
                comp_phys_val = "CAM"  # todo: generalize this special case
            new_compset_text += '_' + comp_phys_val

            # Component Option (optional)
            cv_comp_option = cvars['COMP_{}_OPTION'.format(comp_class)]
            if cv_comp_option.is_none():
                return [''] # not all component options selected yet, so not ready to set COMPSET

            comp_option_val = cv_comp_option.value
            new_compset_text += '%'+comp_option_val
        
        new_compset_text = new_compset_text.replace('%(none)','')
        return [new_compset_text], None


    COMPSET = cvars['COMPSET']
    options_setters.append(
        OptionsSetter(
            var = COMPSET,
            func = compset_func, 
            inducing_vars = [INITTIME] + [cvars["COMP_{}_OPTION".format(comp_class)] for comp_class in ci.comp_classes]  
        )
    )
    
    GRID = cvars['GRID']

    def grid_options_func(compset):

        if compset == "":
            return None, None

        compatible_grids = []
        grid_descriptions = []

        for alias, compset_attr, not_compset_attr, desc in ci.model_grids:
            if compset_attr and not re.search(compset_attr, compset):
                continue
            if not_compset_attr and re.search(not_compset_attr, compset):
                continue
            if GRID.view_mode == 'suggested' and desc == '':
                continue

            comp_grid_dict = ci.retrieve_component_grids(alias, compset)

            try:
                cvars['ATM_GRID'].major_layer.check_assignment(cvars['ATM_GRID'], comp_grid_dict['a%'])
                cvars['LND_GRID'].major_layer.check_assignment(cvars['LND_GRID'], comp_grid_dict['l%'])
                cvars['OCN_GRID'].major_layer.check_assignment(cvars['OCN_GRID'], comp_grid_dict['oi%'])
                cvars['ICE_GRID'].major_layer.check_assignment(cvars['ICE_GRID'], comp_grid_dict['oi%'])
                cvars['ROF_GRID'].major_layer.check_assignment(cvars['ROF_GRID'], comp_grid_dict['r%'])
                cvars['GLC_GRID'].major_layer.check_assignment(cvars['GLC_GRID'], comp_grid_dict['g%'])
                cvars['WAV_GRID'].major_layer.check_assignment(cvars['WAV_GRID'], comp_grid_dict['w%'])
                cvars['MASK_GRID'].major_layer.check_assignment(cvars['MASK_GRID'], comp_grid_dict['m%'])
            except AssertionError:
                continue
        
            compatible_grids.append(alias)
            grid_descriptions.append(desc)

        return compatible_grids, grid_descriptions

    options_setters.append(
        OptionsSetter(
            var = GRID,
            func = grid_options_func,
            inducing_vars = [COMPSET]
        )
    )
    
    return options_setters

