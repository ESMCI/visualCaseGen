from z3 import Implies, And, Or, Not, Contains, PrefixOf
from ProConPy.csp_utils import In

def get_relational_constraints(cvars):
    """ Returns a dictionary of relational constraints for the given config_vars where keys are the z3 boolean expressions
    and values are error messages to be displayed when the constraint is violated.
    """

    # references to ConfigVars appearing in relational constraints
    INITTIME = cvars['INITTIME']
    COMPSET_MODE = cvars['COMPSET_MODE']
    COMP_ATM = cvars['COMP_ATM'];  COMP_ATM_OPTION = cvars['COMP_ATM_OPTION']
    COMP_LND = cvars['COMP_LND'];  COMP_LND_OPTION = cvars['COMP_LND_OPTION']
    COMP_ICE = cvars['COMP_ICE'];  COMP_ICE_OPTION = cvars['COMP_ICE_OPTION']
    COMP_OCN = cvars['COMP_OCN'];  COMP_OCN_OPTION = cvars['COMP_OCN_OPTION']
    COMP_ROF = cvars['COMP_ROF'];  COMP_ROF_OPTION = cvars['COMP_ROF_OPTION']
    COMP_GLC = cvars['COMP_GLC'];  COMP_GLC_OPTION = cvars['COMP_GLC_OPTION']
    COMP_WAV = cvars['COMP_WAV'];  COMP_WAV_OPTION = cvars['COMP_WAV_OPTION']
    GRID_MODE = cvars['GRID_MODE']
    ATM_GRID = cvars['ATM_GRID']
    OCN_GRID = cvars['OCN_GRID']
    WAV_GRID = cvars['WAV_GRID']
    OCN_GRID_MODE = cvars['OCN_GRID_MODE']; OCN_GRID_EXTENT = cvars['OCN_GRID_EXTENT']; OCN_CYCLIC_X = cvars['OCN_CYCLIC_X']
    OCN_NX = cvars['OCN_NX']; OCN_NY = cvars['OCN_NY']; OCN_LENX = cvars['OCN_LENX']; OCN_LENY = cvars['OCN_LENY']
    LND_GRID_MODE = cvars['LND_GRID_MODE']; LND_SOIL_COLOR = cvars['LND_SOIL_COLOR']; LND_DOM_PFT = cvars['LND_DOM_PFT']
    LND_MAX_SAT_AREA = cvars['LND_MAX_SAT_AREA']; LND_STD_ELEV = cvars['LND_STD_ELEV']

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

        Implies(Or(COMP_ROF=="rtm", COMP_ROF=="mosart", COMP_ROF=="mizuroute"), COMP_LND=='clm') :
            "Active runoff models can only be selected if CLM is the land component.",

        Implies(And(In(COMP_OCN, ["pop", "mom"]), COMP_ATM=="datm"), COMP_LND=="slnd") :
            "When MOM|POP is coupled with data atmosphere (datm), LND component must be stub (slnd).",

        Implies(And(COMP_ATM=="datm", COMP_LND=="clm"), And(COMP_ICE=="sice", COMP_OCN=="socn")) :
            "If CLM is coupled with DATM, then both ICE and OCN must be stub.",

        Implies(COMP_ATM=="satm", And(COMP_ICE=="sice", COMP_ROF=="srof", COMP_OCN=="socn")) :
            "An active or data atmosphere model is needed to force ocean, ice, and/or runoff models.",
        
        Implies(COMP_LND=="slnd", COMP_GLC=="sglc") :
            "GLC cannot be coupled with a stub land model.",
        
        Implies(COMP_LND=="slim", And(COMP_GLC=="sglc", COMP_ROF=="srof", COMP_WAV=="swav")) :
            "GLC, ROF, and WAV cannot be coupled with SLIM.",
        
        Implies(COMP_OCN=="socn", COMP_ICE=="sice") :
            "When ocean is made stub, ice must also be stub.",
        
        Implies(COMP_LND=="clm", COMP_ROF!="drof") :
            "CLM cannot be coupled with a data runoff model.",
        
        Implies(COMP_LND=="dlnd", COMP_ATM!="cam") : # TODO: check this constraint.
            "Data land model cannot be coupled with CAM.",
        
        Implies(COMP_OCN=="docn", COMP_OCN_OPTION != "(none)"):
            "Must pick a valid DOCN option.",

        Implies(COMP_ICE=="dice", COMP_ICE_OPTION != "(none)"):
            "Must pick a valid DICE option.",

        Implies(COMP_ATM=="datm", COMP_ATM_OPTION != "(none)"):
            "Must pick a valid DATM option.",

        Implies(COMP_ROF=="drof", COMP_ROF_OPTION != "(none)"):
            "Must pick a valid DROF option.",

        Implies(COMP_WAV=="phys", COMP_WAV_OPTION != "(none)"):
            "Must pick a valid DWAV option.",

        Implies(In(COMP_LND, ["clm", "dlnd"]), COMP_LND_OPTION != "(none)"):
            "Must pick a valid LND option.",

        Implies(COMP_GLC=="cism", COMP_GLC_OPTION != "(none)"):
            "Must pick a valid GLC option.",

        Implies( Not(And(COMP_LND=="slnd", COMP_ICE=="sice", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc", COMP_WAV=="swav")),
                Not(In(COMP_ATM_OPTION, ["ADIAB", "DABIP04", "TJ16", "HS94", "KESSLER"])) ):
            "Simple CAM physics options can only be picked if all other components are stub.",

        Implies(COMP_OCN=="mom", In(OCN_GRID, ["tx2_3v2", "tx0.66v1", "gx1v6", "tx0.25v1"])):
            "Not a valid MOM6 grid.",

        Implies(COMP_OCN=="pop", In(OCN_GRID, ["gx1v6", "gx1v7", "gx3v7", "tx0.1v2", "tx0.1v3", "tx1v1"])):
            "Not a valid POP2 grid.",

        Implies(Contains(COMP_OCN_OPTION, "AQ"), In(OCN_GRID,["0.9x1.25", "1.9x2.5", "4x5"])):
            "When in aquaplanet mode, the ocean grid must be set to f09, f19, or f45",

        Implies(COMP_OCN!="mom", WAV_GRID != "wtx0.66v1"):
            "wt066v1 wave grid is for MOM6 coupling only",

        Implies(COMP_ATM_OPTION != "SCAM", ATM_GRID != "T42"):
            "T42 grid can only be used with SCAM option.",
        
        Implies(Contains(COMP_ATM_OPTION, "JRA"), ATM_GRID == "TL319"):
            "JRA forcing can only be used with TL319 ATM grid.",
        
        Implies(In(COMP_ATM_OPTION, ["IAF", "NYF"]), ATM_GRID == "T62"):
            "Core2 forcing can only be used with T62 grid.",

        # mom6_bathy-related constraints ------------------

        Implies (And(COMP_LND=="slnd", COMP_ICE=="sice"), Or(COMP_OCN!="mom", OCN_GRID_EXTENT!="Global")):
             "LND or ICE must be present to hide Global MOM6 grid poles.",

        Implies(And(COMP_OCN != "mom", COMP_LND!="clm"), GRID_MODE=="Standard"):
            "Custom grids can only be generated when MOM6 and/or CLM are selected.",

        Implies(COMP_OCN!="mom", OCN_GRID_MODE=="Standard"):
            "Custom OCN grids can only be generated for MOM6.",
    
         #todo OCN_GRID_MODE!="Modify Existing":
         #todo     "This feature (Modify Existing) not implemented yet.",

        And(OCN_NX>=2, OCN_NY>=2, (OCN_NX*OCN_NY)>=16 ):
            "MOM6 grid dimensions too small.",

        And(OCN_NX<10000, OCN_NY<10000):
            "MOM6 grid dimensions too big.",
        
        Implies(OCN_GRID_EXTENT=="Regional", COMP_WAV=="swav"):
            "A regional ocean model cannot be coupled with a wave component.",

        Implies(OCN_GRID_EXTENT=="Regional", COMP_ICE=="sice"):
            "A regional ocean model cannot be coupled with an ice component.",

        Implies(OCN_GRID_EXTENT=="Regional", OCN_CYCLIC_X=="False"):
            "Regional ocean domain cannot be reentrant (due to an ESMF limitation.)",

        Implies(OCN_GRID_EXTENT=="Global", OCN_CYCLIC_X=="True"):
            "Global ocean domains must be reentrant in the x-direction.",

        Implies(OCN_GRID_EXTENT=="Global", OCN_LENX==360.0):
            "Global ocean model domains must have a length of 360 degrees in the x-direction.",

        Implies(OCN_GRID_EXTENT=="Global", And(OCN_LENY>0.0, OCN_LENY<=180.0) ):
            "OCN grid length in Y direction must be <= 180.0 when OCN grid extent is global.",

        # Custom lnd grid constraints ------------------
        Implies(COMP_LND!="clm", LND_GRID_MODE=="Standard"):
            "Custom LND grids can only be generated for CLM.",

        And(0<=LND_SOIL_COLOR, LND_SOIL_COLOR<=20):
            "Soil color must be set to an integer value between 0 and 20",

        LND_DOM_PFT >= 0.0:
            "PFT/CFT must be set to a nonnegative number",

        And(0<=LND_MAX_SAT_AREA, LND_MAX_SAT_AREA<=1):
            "Max fraction of saturated area must be set to a value between 0 and 1.",

        LND_STD_ELEV >= 0.0:
            "Standard deviation of elevation must be a nonnegative number."

        #### Assertions to stress-test the CSP solver

        ### Implies(COMP_OCN=="docn", COMP_LND_PHYS!="DLND") : "FOO",

        ### Implies(COMP_OCN=="docn", COMP_ATM_PHYS!="CAM60") : "BAR",

        ### Not(In(COMP_LND_PHYS, ['CLM45', 'CLM50'])) : "BAZ",

    }