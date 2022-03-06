from z3 import Implies, And, Or, Not

class OptionsSetter:
    def __init__(self, var, parent_vars, options_func, tooltips_func=None):
        self.var = var
        self.parent_vars = parent_vars if isinstance(parent_vars, (list, tuple, set)) or parent_vars is None else [parent_vars,]
        self.options_func = options_func
        self.tooltips_func = tooltips_func

def get_options_setters(cvars, ci):

    options_setters = [] 

    INITTIME = cvars['INITTIME']
    options_setters.append(
        OptionsSetter(
            var = INITTIME, 
            parent_vars = None,
            options_func = lambda:['1850', '2000', 'HIST'],
            tooltips_func = lambda:['Pre-industrial', 'Present day', 'Historical'] 
        )
    )

    for comp_class in ci.comp_classes:
        COMP = cvars['COMP_{}'.format(comp_class)]
        options_setters.append(
            OptionsSetter(
                var = COMP,
                parent_vars = None,
                options_func = lambda:[model for model in ci.models[comp_class] if model[0] != 'x']
            )
        )

    for comp_class in ci.comp_classes:
        COMP = cvars['COMP_{}'.format(comp_class)]
        COMP_PHYS = cvars["COMP_{}_PHYS".format(comp_class)]
        options_setters.append(
            OptionsSetter(
                var = COMP_PHYS,
                parent_vars = COMP,
                options_func = lambda model: self.ci.comp_phys[model],
                tooltips_func = lambda model: self.ci.comp_phys[model]
                # where model = COMP.value
            )
        )

    for comp_class in ci.comp_classes:
        COMP = cvars['COMP_{}'.format(comp_class)]
        COMP_PHYS = cvars["COMP_{}_PHYS".format(comp_class)]
        COMP_OPTION = cvars["COMP_{}_OPTION".format(comp_class)]
        options_setters.append(
            OptionsSetter(
                var = COMP_OPTION,
                parent_vars = (COMP, COMP_PHYS),
                options_func = lambda model,phys: self.ci.comp_options[model,phys],
                tooltips_func = lambda model,phys: self.ci.comp_options[model,phys]
                # where model, phys = COMP.value, COMP_PHYS.value
            )
        )
    
    return options_setters

