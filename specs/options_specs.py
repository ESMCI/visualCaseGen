import sys
from z3 import Implies, And, Or, Not, Contains, Concat, If, is_expr, z3util
from visualCaseGen.logic_utils import In
from visualCaseGen.dev_utils import RunError
from z3 import Solver, sat, unsat

sys.path.append('../')

class OptionsSpec:

    def __init__(self, var, options_and_tooltips, inducing_vars=[], cvars=None, options_and_tooltips_dynamic=None):
        self.var = var
        self.var.options_spec = self
        assert isinstance(options_and_tooltips, (dict,tuple))
        self.options_and_tooltips = options_and_tooltips
        self.var.assign_options_spec(self)
        assert isinstance(inducing_vars, list), "inducing_vars parameter must be a list"
        if len(inducing_vars) > 0:
            self.inducing_vars = inducing_vars
        else:
            assert cvars is not None, "cvars dict must be provided if inducing vars is not provided"
            self._determine_inducing_vars(cvars)
        self._options_and_tooltips_dynamic = options_and_tooltips_dynamic

    def __call__(self):
        # this method is only used in dynamic mode

        if any([inducing_var.is_none() for inducing_var in self.inducing_vars]):
            return None, None

        if self._options_and_tooltips_dynamic is not None:
            return self._options_and_tooltips_dynamic()

        elif self.has_propositioned_options():

            # todo, make the below check computationally more efficient
            s = Solver()
            for var in self.inducing_vars:
                if var.value is not None:
                    s.add(var==var.value)
            valid_propositons = []
            for proposition, options_and_tooltips in self.options_and_tooltips.items():
                if s.check(proposition) == sat:
                    valid_propositons.append(proposition)
            assert len(valid_propositons) == 1, "Must have exactly one valid proposition"
            return self.options_and_tooltips[valid_propositons[0]]
        else:
            return self.options_and_tooltips


    def has_propositioned_options(self):
        if isinstance(self.options_and_tooltips, tuple): # single options list with no propositions
            return False
        elif isinstance(self.options_and_tooltips, dict): # multiple options list with propsitions
            return True 
        else:
            raise RunError("Unknown options list type encountered in an OptionsSpec instance.")


    def _determine_inducing_vars(self,cvars):

        inducing_vars = set()

        if self.has_propositioned_options():
            for proposition, options_and_tooltips in self.options_and_tooltips.items():
                if is_expr(proposition):
                    inducing_vars.update(
                        {cvars[var.sexpr()] for var in z3util.get_vars(proposition)}
                    )
                for opt in options_and_tooltips[0]:
                    if is_expr(opt):
                        inducing_vars.update(
                            {cvars[var.sexpr()] for var in z3util.get_vars(opt)}
                        )
        else:
            for opt in self.options_and_tooltips[0]:
                if is_expr(opt):
                    inducing_vars.update(
                        {cvars[var.sexpr()] for var in z3util.get_vars(opt)}
                    )


        self.inducing_vars = list(inducing_vars)

    def has_inducing_vars(self):
        return len(self.inducing_vars)>0

    def get_options(self):

        options = []

        if self.has_propositioned_options():
            for proposition, options_and_tooltips in self.options_and_tooltips.items():
                options.extend(options_and_tooltips[0])
        else:
            options.extend(self.options_and_tooltips[0])

        return options

    def get_options_assertions(self):

        assertions = None

        if self.has_propositioned_options():
            assertions = [
                Implies(proposition, In(self.var, options_and_tooltips[0]))
                for proposition, options_and_tooltips in self.var.options_spec.options_and_tooltips.items()
            ]
        else:
            assertions = [In(self.var, self.var.options_spec.options_and_tooltips[0])]

        return assertions

    def write_all_options_specs(cvars, filename):
        with open(filename, 'w') as file:
            for varname, var in cvars.items():
                if hasattr(var, 'options_spec'):
                    assertions = var._options_spec.get_options_assertions()
                    for assertion in assertions:
                        file.write(str(assertion))
                        file.write('\n')


def get_options_specs(cvars, ci):

    # INITTIME
    INITTIME = cvars['INITTIME']
    OptionsSpec(
        var = INITTIME,
        options_and_tooltips = (
            ['1850', '2000', 'HIST'],
            ['Pre-industrial', 'Present day', 'Historical']
        ),
        cvars = cvars
    )

    # COMP_???
    for comp_class in ci.comp_classes:
        COMP = cvars[f'COMP_{comp_class}']
        OptionsSpec(
            var = COMP,
            options_and_tooltips = (
                [model for model in ci.models[comp_class] if model[0] != 'x'],
                None
            ),
            cvars = cvars
        )

    # COMP_???_PHYS
    for comp_class in ci.comp_classes:
        COMP = cvars[f'COMP_{comp_class}']
        COMP_PHYS = cvars[f'COMP_{comp_class}_PHYS']
        OptionsSpec(
            var = COMP_PHYS,
            options_and_tooltips = {
                COMP==model: (
                    ci.comp_phys[model],
                    ci.comp_phys_desc[model]
                )
                for model in ci.models[comp_class] if model[0] != 'x'
            },
            cvars = cvars
        )

    # COMP_???_OPTION
    for comp_class in ci.comp_classes:
        COMP = cvars[f'COMP_{comp_class}']
        COMP_PHYS = cvars[f'COMP_{comp_class}_PHYS']
        COMP_OPTION = cvars[f'COMP_{comp_class}_OPTION']
        OptionsSpec(
            var = COMP_OPTION,
            options_and_tooltips = {
                COMP_PHYS==phys: (
                    ['(none)']+ci.comp_options[model][phys],
                    ['(none)']+ci.comp_options_desc[model][phys]
                )
                for model in ci.models[comp_class] if model[0] != 'x' for phys in ci.comp_phys[model]
            },
            cvars = cvars
        )

    # COMPSET

    def compset_func():

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
    COMP_ATM = cvars['COMP_ATM'];  COMP_ATM_PHYS = cvars['COMP_ATM_PHYS'];  COMP_ATM_OPTION = cvars['COMP_ATM_OPTION']
    COMP_LND = cvars['COMP_LND'];  COMP_LND_PHYS = cvars['COMP_LND_PHYS'];  COMP_LND_OPTION = cvars['COMP_LND_OPTION']
    COMP_ICE = cvars['COMP_ICE'];  COMP_ICE_PHYS = cvars['COMP_ICE_PHYS'];  COMP_ICE_OPTION = cvars['COMP_ICE_OPTION']
    COMP_OCN = cvars['COMP_OCN'];  COMP_OCN_PHYS = cvars['COMP_OCN_PHYS'];  COMP_OCN_OPTION = cvars['COMP_OCN_OPTION']
    COMP_ROF = cvars['COMP_ROF'];  COMP_ROF_PHYS = cvars['COMP_ROF_PHYS'];  COMP_ROF_OPTION = cvars['COMP_ROF_OPTION']
    COMP_GLC = cvars['COMP_GLC'];  COMP_GLC_PHYS = cvars['COMP_GLC_PHYS'];  COMP_GLC_OPTION = cvars['COMP_GLC_OPTION']
    COMP_WAV = cvars['COMP_WAV'];  COMP_WAV_PHYS = cvars['COMP_WAV_PHYS'];  COMP_WAV_OPTION = cvars['COMP_WAV_OPTION']
    OptionsSpec(
        var = COMPSET,
        options_and_tooltips = (
             [Concat(
                INITTIME,
                '_',
                If(COMP_ATM_OPTION=="(none)", COMP_ATM_PHYS, Concat(COMP_ATM_PHYS,'%',COMP_ATM_OPTION)),
                "_",
                If(COMP_LND_OPTION=="(none)", COMP_LND_PHYS, Concat(COMP_LND_PHYS,'%',COMP_LND_OPTION)),
                "_",
                If(COMP_ICE_OPTION=="(none)", COMP_ICE_PHYS, Concat(COMP_ICE_PHYS,'%',COMP_ICE_OPTION)),
                "_",
                If(COMP_OCN_OPTION=="(none)", COMP_OCN_PHYS, Concat(COMP_OCN_PHYS,'%',COMP_OCN_OPTION)),
                "_",
                If(COMP_ROF_OPTION=="(none)", COMP_ROF_PHYS, Concat(COMP_ROF_PHYS,'%',COMP_ROF_OPTION)),
                "_",
                If(COMP_GLC_OPTION=="(none)", COMP_GLC_PHYS, Concat(COMP_GLC_PHYS,'%',COMP_GLC_OPTION)),
                "_",
                If(COMP_WAV_OPTION=="(none)", COMP_WAV_PHYS, Concat(COMP_WAV_PHYS,'%',COMP_WAV_OPTION)),
            )],
            None
        ),
        cvars = cvars,
        options_and_tooltips_dynamic = compset_func
    )

    # GRID
    GRID = cvars['GRID']
    grid_opts = {}
    for alias, compset_attr, not_compset_attr, desc in ci.model_grids:
        if compset_attr is None and not_compset_attr is None:
            if not True in grid_opts:
                grid_opts[True] = ([],[])
            grid_opts[True][0].append(alias)
            grid_opts[True][1].append(desc)

        else:
            pass

    OptionsSpec(
        var = GRID,
        options_and_tooltips = grid_opts,
        inducing_vars=[COMPSET]
    )


    ## # GRID
    ## opts['GRID'] = {"? True": []}
    ## for alias, compset_attr, not_compset_attr, desc in ci.model_grids:
    ##     if compset_attr is None and not_compset_attr is None:
    ##         opts['GRID']["? True"].append(alias)
    ##     else:
    ##         guard = "?"
    ##         if compset_attr is not None:
    ##             guard += f" {compset_attr}"
    ##         if not_compset_attr is not None:
    ##             guard += f" not {not_compset_attr}"

    ##         if guard not in opts['GRID']:
    ##             opts['GRID'][guard] = []

    ##         opts['GRID'][guard].append(alias)
