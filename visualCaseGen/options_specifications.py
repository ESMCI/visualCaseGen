from ProConPy.config_var import cvars

def set_options(cime):

    cv_compset_mode = cvars["COMPSET_MODE"]
    cv_compset_mode.options = ["Predefined", "Custom"]
    cv_compset_mode.tooltips = ["Select from a list of predefined compsets", 
                            "Construct a custom compset"]

    cv_inittime = cvars["INITTIME"]
    cv_inittime.options = ["1850", "2000", "HIST"]
    cv_inittime.tooltips = ["Pre-industrial", "Present day", "Historical"]