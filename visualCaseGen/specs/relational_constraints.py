from z3 import Implies, And, Or, Not, Contains
from ProConPy.csp_utils import In

def get_relational_constraints(cvars):
    """ Returns a dictionary of relational constraints for the given config_vars where keys are the z3 boolean expressions
    and values are error messages to be displayed when the constraint is violated.
    """

    # references to ConfigVars appearing in relational constraints
    INITTIME = cvars['INITTIME']
    COMPSET_MODE = cvars['COMPSET_MODE']
    COMP_ATM = cvars['COMP_ATM'];  COMP_ATM_PHYS = cvars['COMP_ATM_PHYS'];  COMP_ATM_OPTION = cvars['COMP_ATM_OPTION']
    COMP_LND = cvars['COMP_LND'];  COMP_LND_PHYS = cvars['COMP_LND_PHYS'];  COMP_LND_OPTION = cvars['COMP_LND_OPTION']
    COMP_ICE = cvars['COMP_ICE'];  COMP_ICE_PHYS = cvars['COMP_ICE_PHYS'];  COMP_ICE_OPTION = cvars['COMP_ICE_OPTION']
    COMP_OCN = cvars['COMP_OCN'];  COMP_OCN_PHYS = cvars['COMP_OCN_PHYS'];  COMP_OCN_OPTION = cvars['COMP_OCN_OPTION']
    COMP_ROF = cvars['COMP_ROF'];  COMP_ROF_PHYS = cvars['COMP_ROF_PHYS'];  COMP_ROF_OPTION = cvars['COMP_ROF_OPTION']
    COMP_GLC = cvars['COMP_GLC'];  COMP_GLC_PHYS = cvars['COMP_GLC_PHYS'];  COMP_GLC_OPTION = cvars['COMP_GLC_OPTION']
    COMP_WAV = cvars['COMP_WAV'];  COMP_WAV_PHYS = cvars['COMP_WAV_PHYS'];  COMP_WAV_OPTION = cvars['COMP_WAV_OPTION']
    COMPSET_LNAME = cvars['COMPSET_LNAME']
    GRID_MODE = cvars['COMPSET_MODE']
    ATM_GRID = cvars['ATM_GRID']
    OCN_GRID = cvars['OCN_GRID']
    WAV_GRID = cvars['WAV_GRID']

    # Return a dictionary of constraints where keys are the z3 boolean expressions corresponding to the constraints
    # and values are error messages to be displayed when the constraint is violated.
    return {

        Not(And(COMP_ATM=="satm", COMP_LND=="slnd", COMP_ICE=="sice", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc", COMP_WAV=="swav")) :
            "At least one component must be an active or a data model",

        Implies(COMP_OCN=="mom", COMP_WAV!="dwav") :
            "MOM6 cannot be coupled with data wave component.",

        Implies(COMP_ATM=="cam", COMP_ICE!="dice") :
            "CAM cannot be coupled with Data ICE.",

        Implies(COMP_WAV=="ww3", In(COMP_OCN, ["mom", "pop"])) :
            "WW3 can only be selected if either POP2 or MOM6 is the ocean component.",

        Implies(Or(COMP_ROF=="rtm", COMP_ROF=="mosart"), COMP_LND=='clm') :
            "RTM or MOSART can only be selected if CLM is the land component.",

        Implies(And(In(COMP_OCN, ["pop", "mom"]), COMP_ATM=="datm"), COMP_LND=="slnd") :
            "When MOM|POP is coupled with data atmosphere (datm), LND component must be stub (slnd).",

        ###todo Implies (And(COMP_LND=="slnd", COMP_ICE=="sice"), Or(COMP_OCN!="mom", OCN_GRID_EXTENT!="Global")):
        ###todo      "LND or ICE must be present to hide Global MOM6 grid poles.",

        Implies(And(COMP_ATM=="datm", COMP_LND=="clm"), And(COMP_ICE=="sice", COMP_OCN=="socn")) :
            "If CLM is coupled with DATM, then both ICE and OCN must be stub.",

        Implies(In(COMP_OCN, ["mom", "pop"]), COMP_ATM!="satm") :
            "If the ocean component is active, then the atmosphere component cannot be made stub.",
        
        Implies(COMP_OCN_PHYS=="DOCN", COMP_OCN_OPTION != "(none)"):
            "Must pick a valid DOCN option.",

        Implies(COMP_ICE_PHYS=="DICE", COMP_ICE_OPTION != "(none)"):
            "Must pick a valid DICE option.",

        Implies(COMP_ATM_PHYS=="DATM", COMP_ATM_OPTION != "(none)"):
            "Must pick a valid DATM option.",

        Implies(COMP_ROF_PHYS=="DROF", COMP_ROF_OPTION != "(none)"):
            "Must pick a valid DROF option.",

        Implies(COMP_WAV_PHYS=="DWAV", COMP_WAV_OPTION != "(none)"):
            "Must pick a valid DWAV option.",

        Implies(In(COMP_LND, ["clm", "dlnd"]), COMP_LND_OPTION != "(none)"):
            "Must pick a valid LND option.",

        Implies(COMP_GLC=="cism", COMP_GLC_OPTION != "(none)"):
            "Must pick a valid GLC option.",

        Implies( Not(And(COMP_LND=="slnd", COMP_ICE=="sice", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc", COMP_WAV=="swav")),
                Not(In(COMP_ATM_OPTION, ["ADIAB", "DABIP04", "TJ16", "HS94", "KESSLER"])) ):
            "Simple CAM physics options can only be picked if all other components are stub.",

        Implies(Contains(COMPSET_LNAME, "MOM6"), In(OCN_GRID, ["tx2_3v2", "tx0.66v1", "gx1v6", "tx0.25v1"])):
            "Not a valid MOM6 grid.",

        Implies(Contains(COMP_OCN_OPTION, "AQ"), In(OCN_GRID,["0.9x1.25", "1.9x2.5", "4x5"])):
            "When in aquaplanet mode, the ocean grid must be set to f09, f19, or f45",

        Implies(COMP_OCN!="mom", WAV_GRID != "wtx0.66v1"):
            "wt066v1 wave grid is for MOM6 coupling only",

        Implies(COMP_ATM_OPTION != "SCAM", ATM_GRID != "T42"):
            "T42 grid can only be used with SCAM option.",


        #### Assertions to stress-test the CSP solver

        ### Implies(COMP_OCN=="docn", COMP_LND_PHYS!="DLND") : "FOO",

        ### Implies(COMP_OCN=="docn", COMP_ATM_PHYS!="CAM60") : "BAR",

        ### Not(In(COMP_LND_PHYS, ['CLM45', 'CLM50'])) : "BAZ",

    }