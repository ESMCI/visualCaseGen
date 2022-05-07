import sys
from z3 import Implies, And, Or, Not, Contains, Concat, If, Length, StringVal
from visualCaseGen.logic_utils import In

sys.path.append('../')

class OptionsSpec:

    def __init__(self, var, opts):
        self.var = var
        self.var.options_spec = self
        assert isinstance(opts, (dict,tuple))
        self.opts = opts

    @staticmethod
    def get_options(var):

        options = []

        if hasattr(var, 'options_spec'):

            if isinstance(var.options_spec.opts, tuple):
                # single options list
                options.extend(var.options_spec.opts[0])
            elif isinstance(var.options_spec.opts, dict):
                # multiple options list with propositiions
                for condition, opts_list in var.options_spec.opts.items():
                    options.extend(opts_list[0])
        else:
            raise RuntimeError("Variable doesn't have options_spec property.")

        return options
    
    @staticmethod
    def get_options_assertions(var):

        assertions = None

        if hasattr(var, 'options_spec'):

            if isinstance(var.options_spec.opts, tuple):
                # single options list
                assertions = [In(var, var.options_spec.opts[0])]

            elif isinstance(var.options_spec.opts, dict):
                # multiple options list with propositiions
                assertions = [
                    Implies(condition, In(var, opts_list[0]))
                    for condition, opts_list in var.options_spec.opts.items()
                ]

        return assertions

    @staticmethod
    def write_all_options_specs(cvars, filename):
        with open(filename, 'w') as file:
            for varname, var in cvars.items():
                if hasattr(var, 'options_spec'):
                    assertions = OptionsSpec.get_options_assertions(var)
                    for assertion in assertions:
                        file.write(str(assertion))
                        file.write('\n')
    

def gen_options_specs(cvars, ci):

    # INITTIME
    INITTIME = cvars['INITTIME']
    OptionsSpec(
        var = INITTIME,
        opts = (
            ['1850', '2000', 'HIST'],
            ['Pre-industrial', 'Present day', 'Historical']
        ) 
    )

    # COMP_???
    for comp_class in ci.comp_classes:
        COMP = cvars[f'COMP_{comp_class}']
        OptionsSpec(
            var = COMP,
            opts = (
                [model for model in ci.models[comp_class] if model[0] != 'x'],
                None
            )
        )
    
    # COMP_???_PHYS
    for comp_class in ci.comp_classes:
        COMP = cvars[f'COMP_{comp_class}']
        COMP_PHYS = cvars[f'COMP_{comp_class}_PHYS']
        OptionsSpec(
            var = COMP_PHYS,
            opts = {
                COMP==model: (
                    ci.comp_phys[model],
                    ci.comp_phys_desc[model]
                )
                for model in ci.models[comp_class] if model[0] != 'x'
            }
        )

    # COMP_???_OPTION
    for comp_class in ci.comp_classes:
        COMP = cvars[f'COMP_{comp_class}']
        COMP_PHYS = cvars[f'COMP_{comp_class}_PHYS']
        COMP_OPTION = cvars[f'COMP_{comp_class}_OPTION']
        OptionsSpec(
            var = COMP_OPTION,
            opts = {
                COMP_PHYS==phys: (
                    ['(none)']+ci.comp_options[model][phys],
                    ['(none)']+ci.comp_options_desc[model][phys]
                )
                for model in ci.models[comp_class] if model[0] != 'x' for phys in ci.comp_phys[model]
            }
        )
    
    # COMPSET
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
        opts = (
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
        )
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
        opts = grid_opts
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
