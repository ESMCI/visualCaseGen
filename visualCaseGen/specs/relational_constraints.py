from z3 import Implies, And, Or, Not, Contains, PrefixOf
from ProConPy.csp_utils import In

def get_relational_constraints(cvars):
    """ Returns a dictionary of relational constraints for the given config_vars where keys are the z3 boolean expressions
    and values are error messages to be displayed when the constraint is violated.
    """

    # references to ConfigVars appearing in relational constraints
    INITTIME = cvars['INITTIME']
    COMPSET_MODE = cvars['COMPSET_MODE']
    CUSTOM_ATM = cvars['CUSTOM_ATM'];  CUSTOM_ATM_PHYS = cvars['CUSTOM_ATM_PHYS'];  CUSTOM_ATM_OPTION = cvars['CUSTOM_ATM_OPTION']
    CUSTOM_LND = cvars['CUSTOM_LND'];  CUSTOM_LND_PHYS = cvars['CUSTOM_LND_PHYS'];  CUSTOM_LND_OPTION = cvars['CUSTOM_LND_OPTION']
    CUSTOM_ICE = cvars['CUSTOM_ICE'];  CUSTOM_ICE_PHYS = cvars['CUSTOM_ICE_PHYS'];  CUSTOM_ICE_OPTION = cvars['CUSTOM_ICE_OPTION']
    CUSTOM_OCN = cvars['CUSTOM_OCN'];  CUSTOM_OCN_PHYS = cvars['CUSTOM_OCN_PHYS'];  CUSTOM_OCN_OPTION = cvars['CUSTOM_OCN_OPTION']
    CUSTOM_ROF = cvars['CUSTOM_ROF'];  CUSTOM_ROF_PHYS = cvars['CUSTOM_ROF_PHYS'];  CUSTOM_ROF_OPTION = cvars['CUSTOM_ROF_OPTION']
    CUSTOM_GLC = cvars['CUSTOM_GLC'];  CUSTOM_GLC_PHYS = cvars['CUSTOM_GLC_PHYS'];  CUSTOM_GLC_OPTION = cvars['CUSTOM_GLC_OPTION']
    CUSTOM_WAV = cvars['CUSTOM_WAV'];  CUSTOM_WAV_PHYS = cvars['CUSTOM_WAV_PHYS'];  CUSTOM_WAV_OPTION = cvars['CUSTOM_WAV_OPTION']
    COMP_ATM_PHYS = cvars['COMP_ATM_PHYS']
    COMP_LND_PHYS = cvars['COMP_LND_PHYS']
    COMP_ICE_PHYS = cvars['COMP_ICE_PHYS']
    COMP_OCN_PHYS = cvars['COMP_OCN_PHYS']
    COMP_ROF_PHYS = cvars['COMP_ROF_PHYS']
    COMP_GLC_PHYS = cvars['COMP_GLC_PHYS']
    COMP_WAV_PHYS = cvars['COMP_WAV_PHYS']
    GRID_MODE = cvars['COMPSET_MODE']
    ATM_GRID = cvars['ATM_GRID']
    OCN_GRID = cvars['OCN_GRID']
    WAV_GRID = cvars['WAV_GRID']
    OCN_GRID_MODE = cvars['OCN_GRID_MODE']; OCN_GRID_EXTENT = cvars['OCN_GRID_EXTENT']; OCN_CYCLIC_X = cvars['OCN_CYCLIC_X']
    OCN_NX = cvars['OCN_NX']; OCN_NY = cvars['OCN_NY']; OCN_LENX = cvars['OCN_LENX']; OCN_LENY = cvars['OCN_LENY']

    # Return a dictionary of constraints where keys are the z3 boolean expressions corresponding to the constraints
    # and values are error messages to be displayed when the constraint is violated.
    return {

        Not(And(CUSTOM_ATM=="satm", CUSTOM_LND=="slnd", CUSTOM_ICE=="sice", CUSTOM_OCN=="socn", CUSTOM_ROF=="srof", CUSTOM_GLC=="sglc", CUSTOM_WAV=="swav")) :
            "At least one component must be an active or a data model",

        Implies(CUSTOM_OCN=="mom", CUSTOM_WAV!="dwav") :
            "MOM6 cannot be coupled with data wave component.",

        Implies(CUSTOM_ATM=="cam", CUSTOM_ICE!="dice") :
            "CAM cannot be coupled with Data ICE.",

        Implies(CUSTOM_WAV=="ww3", In(CUSTOM_OCN, ["mom", "pop"])) :
            "WW3 can only be selected if either POP2 or MOM6 is the ocean component.",

        Implies(Or(CUSTOM_ROF=="rtm", CUSTOM_ROF=="mosart"), CUSTOM_LND=='clm') :
            "RTM or MOSART can only be selected if CLM is the land component.",

        Implies(And(In(CUSTOM_OCN, ["pop", "mom"]), CUSTOM_ATM=="datm"), CUSTOM_LND=="slnd") :
            "When MOM|POP is coupled with data atmosphere (datm), LND component must be stub (slnd).",

        Implies(And(CUSTOM_ATM=="datm", CUSTOM_LND=="clm"), And(CUSTOM_ICE=="sice", CUSTOM_OCN=="socn")) :
            "If CLM is coupled with DATM, then both ICE and OCN must be stub.",

        Implies(In(CUSTOM_OCN, ["mom", "pop"]), CUSTOM_ATM!="satm") :
            "If the ocean component is active, then the atmosphere component cannot be made stub.",
        
        Implies(CUSTOM_OCN_PHYS=="DOCN", CUSTOM_OCN_OPTION != "(none)"):
            "Must pick a valid DOCN option.",

        Implies(CUSTOM_ICE_PHYS=="DICE", CUSTOM_ICE_OPTION != "(none)"):
            "Must pick a valid DICE option.",

        Implies(CUSTOM_ATM_PHYS=="DATM", CUSTOM_ATM_OPTION != "(none)"):
            "Must pick a valid DATM option.",

        Implies(CUSTOM_ROF_PHYS=="DROF", CUSTOM_ROF_OPTION != "(none)"):
            "Must pick a valid DROF option.",

        Implies(CUSTOM_WAV_PHYS=="DWAV", CUSTOM_WAV_OPTION != "(none)"):
            "Must pick a valid DWAV option.",

        Implies(In(CUSTOM_LND, ["clm", "dlnd"]), CUSTOM_LND_OPTION != "(none)"):
            "Must pick a valid LND option.",

        Implies(CUSTOM_GLC=="cism", CUSTOM_GLC_OPTION != "(none)"):
            "Must pick a valid GLC option.",

        Implies( Not(And(CUSTOM_LND=="slnd", CUSTOM_ICE=="sice", CUSTOM_OCN=="socn", CUSTOM_ROF=="srof", CUSTOM_GLC=="sglc", CUSTOM_WAV=="swav")),
                Not(In(CUSTOM_ATM_OPTION, ["ADIAB", "DABIP04", "TJ16", "HS94", "KESSLER"])) ):
            "Simple CAM physics options can only be picked if all other components are stub.",

        Implies(COMP_OCN_PHYS=="MOM6", In(OCN_GRID, ["tx2_3v2", "tx0.66v1", "gx1v6", "tx0.25v1"])):
            "Not a valid MOM6 grid.",

        Implies(COMP_OCN_PHYS=="POP2", In(OCN_GRID, ["gx1v6", "gx1v7", "gx3v7", "tx0.1v2", "tx0.1v3", "tx1v1"])):
            "Not a valid POP2 grid.",

        Implies(Contains(CUSTOM_OCN_OPTION, "AQ"), In(OCN_GRID,["0.9x1.25", "1.9x2.5", "4x5"])):
            "When in aquaplanet mode, the ocean grid must be set to f09, f19, or f45",

        Implies(CUSTOM_OCN!="mom", WAV_GRID != "wtx0.66v1"):
            "wt066v1 wave grid is for MOM6 coupling only",

        Implies(CUSTOM_ATM_OPTION != "SCAM", ATM_GRID != "T42"):
            "T42 grid can only be used with SCAM option.",
        
        # mom6_bathy-related constraints

        Implies (And(CUSTOM_LND=="slnd", CUSTOM_ICE=="sice"), Or(CUSTOM_OCN!="mom", OCN_GRID_EXTENT!="Global")):
             "LND or ICE must be present to hide Global MOM6 grid poles.",

        Implies(And(COMP_OCN_PHYS != "MOM6", COMP_LND_PHYS!="CLM"), GRID_MODE!="Custom"):
            "Custom grids can only be generated when MOM6 or CLM are selected.",

        Implies(COMP_OCN_PHYS!="MOM6", OCN_GRID_MODE=="Standard"):
            "Custom OCN grids can only be generated for MOM6.",
    
        #todo OCN_GRID_MODE!="Modify Existing":
        #todo     "This feature (Modify Existing) not implemented yet.",

        And(OCN_NX>=2, OCN_NY>=2, (OCN_NX*OCN_NY)>=16 ):
            "MOM6 grid dimensions too small.",

        And(OCN_NX<10000, OCN_NY<10000):
            "MOM6 grid dimensions too big.",
        
        Implies(OCN_GRID_EXTENT=="Regional", COMP_WAV_PHYS=="SWAV"):
            "A regional ocean model cannot be coupled with a wave component.",

        Implies(OCN_GRID_EXTENT=="Regional", COMP_ICE_PHYS=="SICE"):
           "A regional ocean model cannot be coupled with an ice component.",

        Implies(OCN_GRID_EXTENT=="Regional", OCN_CYCLIC_X=="No"):
            "Regional ocean domain cannot be reentrant (due to an ESMF limitation.)",

        Implies(OCN_GRID_EXTENT=="Global", OCN_CYCLIC_X=="Yes"):
            "Global ocean domains must be reentrant in the x-direction.",

        Implies(OCN_GRID_EXTENT=="Global", OCN_LENX==360.0):
            "Global ocean model domains musth have a length of 360 degrees in the x-direction.",

        Implies(OCN_GRID_EXTENT=="Global", And(OCN_LENY>0.0, OCN_LENY<=180.0) ):
            "OCN grid length in Y direction must be less than or equal to 180.0 when OCN grid extent is global.",

        #### Assertions to stress-test the CSP solver

        ### Implies(CUSTOM_OCN=="docn", CUSTOM_LND_PHYS!="DLND") : "FOO",

        ### Implies(CUSTOM_OCN=="docn", CUSTOM_ATM_PHYS!="CAM60") : "BAR",

        ### Not(In(CUSTOM_LND_PHYS, ['CLM45', 'CLM50'])) : "BAZ",

    }