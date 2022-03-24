from z3 import Implies, And, Or, Not

class OptionsSetter:
    def __init__(self, var, options_func, tooltips_func=None, inducing_vars=[]):

        self.var = var
        self._options_func = options_func
        self._tooltips_func = tooltips_func
        assert isinstance(inducing_vars, list), "incuding_vars parameter must be a list"
        self._inducing_vars = inducing_vars
        self.var.assign_options_setter(self)

    def __call__(self):

        if any([inducing_var.is_none() for inducing_var in self._inducing_vars]):
            return None, None

        options = self._options_func(*(var.value for var in self._inducing_vars))
        tooltips = self._tooltips_func(*(var.value for var in self._inducing_vars)) \
                    if self._tooltips_func is not None else None 
        
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
            options_func = lambda:['1850', '2000', 'HIST'],
            tooltips_func = lambda:['Pre-industrial', 'Present day', 'Historical'] 
        )
    )

    for comp_class in ci.comp_classes:
        COMP = cvars['COMP_{}'.format(comp_class)]
        options_setters.append(
            OptionsSetter(
                var = COMP,
                options_func = lambda cc=comp_class:
                    [model for model in ci.models[cc] if model[0] != 'x'] 
            )
        )

    for comp_class in ci.comp_classes:
        COMP = cvars['COMP_{}'.format(comp_class)]
        COMP_PHYS = cvars["COMP_{}_PHYS".format(comp_class)]
        options_setters.append(
            OptionsSetter(
                var = COMP_PHYS,
                options_func = lambda model: ci.comp_phys[model],
                tooltips_func = lambda model: ci.comp_phys_desc[model],
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
                options_func = lambda model,phys: ['(none)']+ci.comp_options[model][phys],
                tooltips_func = lambda model,phys: ['no modifiers']+ci.comp_options_desc[model][phys],
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
        return [new_compset_text]


    COMPSET = cvars['COMPSET']
    options_setters.append(
        OptionsSetter(
            var = COMPSET,
            options_func = compset_func, 
            inducing_vars = [INITTIME] + [cvars["COMP_{}_OPTION".format(comp_class)] for comp_class in ci.comp_classes]  
        )
    )
    
    #def grid_options_func(
    #    comp_atm_option, comp_lnd_option, comp_ice_option, comp_ocn_option,
    #    comp_rof_option, comp_glc_option, comp_wav_option
    #):

    #    compatible_grids = []
    #    grid_descriptions = []
    #    
    #    return ['a', 'b', comp_atm_option, comp_ocn_option]

    #GRID = cvars['GRID']
    #options_setters.append(
    #    OptionsSetter(
    #        var = GRID,
    #        options_func = grid_options_func,
    #        tooltips_func = grid_options_func,
    #        inducing_vars = [cvars["COMP_{}_OPTION".format(comp_class)] for comp_class in ci.comp_classes]
    #    )
    #)
    
    return options_setters

