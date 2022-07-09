import logging
from visualCaseGen.config_var import ConfigVar
from visualCaseGen.config_var_int import ConfigVarInt
from visualCaseGen.config_var_str import ConfigVarStr
from visualCaseGen.config_var_str_ms import ConfigVarStrMS
from visualCaseGen.config_var_compset import ConfigVarCompset

logger = logging.getLogger('\t'+__name__.split('.')[-1])

def init_configvars(ci, predefined_mode=False):
    """ Define the ConfigVars and, by doing so, register them with the logic engine. """
    logger.debug("Initializing ConfigVars...")

    ConfigVarInt('ILI')
    ConfigVarStr('INITTIME')
    for comp_class in ci.comp_classes:
        ConfigVarStr('COMP_'+str(comp_class))
        ConfigVarStr('COMP_{}_PHYS'.format(comp_class), always_set=True)
        ConfigVarStrMS('COMP_{}_OPTION'.format(comp_class), always_set=True)
        ConfigVarStr('{}_GRID'.format(comp_class))
    if predefined_mode is True:
        for comp_class in ci.comp_classes:
            # Note, COMP_???_FILTER are the only component-related variables shown in the frontend.
            # The rest of the component-related variables are either used at backend or not used at all,
            # but need to be defined so as to parse the option_setters and relational assertions.
            ConfigVarStr('COMP_{}_FILTER'.format(comp_class))
        ConfigVarStr("COMPSET", always_set=True)
    else:
        ConfigVarCompset("COMPSET", always_set=True)
    ConfigVarStr('MASK_GRID')
    cv_grid = ConfigVarStrMS('GRID')
    cv_grid.view_mode = 'suggested' # or 'all'
    ConfigVar.lock()
