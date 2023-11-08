from z3 import Implies, And, Or, Not, Contains
from visualCaseGen.logic_utils import In, When

def relational_assertions_setter(cvars):

    # define references to ConfigVars
    INITTIME = cvars['INITTIME']
    COMP_ATM = cvars['COMP_ATM'];  COMP_ATM_PHYS = cvars['COMP_ATM_PHYS'];  COMP_ATM_OPTION = cvars['COMP_ATM_OPTION']
    COMP_LND = cvars['COMP_LND'];  COMP_LND_PHYS = cvars['COMP_LND_PHYS'];  COMP_LND_OPTION = cvars['COMP_LND_OPTION']
    COMP_ICE = cvars['COMP_ICE'];  COMP_ICE_PHYS = cvars['COMP_ICE_PHYS'];  COMP_ICE_OPTION = cvars['COMP_ICE_OPTION']
    COMP_OCN = cvars['COMP_OCN'];  COMP_OCN_PHYS = cvars['COMP_OCN_PHYS'];  COMP_OCN_OPTION = cvars['COMP_OCN_OPTION']
    COMP_ROF = cvars['COMP_ROF'];  COMP_ROF_PHYS = cvars['COMP_ROF_PHYS'];  COMP_ROF_OPTION = cvars['COMP_ROF_OPTION']
    COMP_GLC = cvars['COMP_GLC'];  COMP_GLC_PHYS = cvars['COMP_GLC_PHYS'];  COMP_GLC_OPTION = cvars['COMP_GLC_OPTION']
    COMP_WAV = cvars['COMP_WAV'];  COMP_WAV_PHYS = cvars['COMP_WAV_PHYS'];  COMP_WAV_OPTION = cvars['COMP_WAV_OPTION']
    ATM_GRID = cvars['ATM_GRID']
    OCN_GRID = cvars['OCN_GRID']
    WAV_GRID = cvars['WAV_GRID']
    GRID = cvars['GRID']
    GRID_MODE = cvars['GRID_MODE']
    OCN_GRID_EXTENT = cvars['OCN_GRID_EXTENT']
    OCN_NX = cvars['OCN_NX']; OCN_NY = cvars['OCN_NY']; OCN_LENX = cvars['OCN_LENX']; OCN_LENY = cvars['OCN_LENY']
    OCN_CYCLIC_X = cvars['OCN_CYCLIC_X']
    LND_SOIL_COLOR = cvars['LND_SOIL_COLOR']; LND_DOM_PFT = cvars['LND_DOM_PFT']; LND_MAX_SAT_AREA = cvars['LND_MAX_SAT_AREA']
    LND_STD_ELEV = cvars['LND_STD_ELEV']

    # The dictionary of assertions where keys are the assertions and values are the associated error messages
    assertions_dict = {

        Not(And(COMP_ATM=="satm", COMP_LND=="slnd", COMP_ICE=="sice", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc", COMP_WAV=="swav")) :
            "Cannot set all components to stub models.",

        #Implies(COMP_ICE=="sice", And(COMP_LND=="slnd", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc") ) :
        #    "If COMP_ICE is stub, all other components must be stub (except for ATM)",

        Implies(COMP_OCN=="mom", COMP_WAV!="dwav") :
            "MOM6 cannot be coupled with data wave component.",

        Implies(COMP_ATM=="cam", COMP_ICE!="dice") :
            "CAM cannot be coupled with Data ICE.",

        Implies(COMP_WAV=="ww3", In(COMP_OCN, ["mom", "pop"])) :
            "WW3 can only be selected if either POP2 or MOM6 is the ocean component.",

        Implies(Or(COMP_ROF=="rtm", COMP_ROF=="mosart"), COMP_LND=='clm') :
            "If running with RTM|MOSART, CLM must be selected as the land component.",

        Implies(And(In(COMP_OCN, ["pop", "mom"]), COMP_ATM=="datm"), COMP_LND=="slnd") :
            "When MOM|POP is forced with DATM, LND must be stub.",

        Implies (And(COMP_LND=="slnd", COMP_ICE=="sice"), Or(COMP_OCN!="mom", OCN_GRID_EXTENT!="Global")):
             "LND or ICE must be present to hide Global MOM6 grid poles.",

        Implies(And(COMP_ATM=="datm", COMP_LND=="clm"), And(COMP_ICE=="sice", COMP_OCN=="socn")) :
            "If CLM is coupled with DATM, then both ICE and OCN must be stub.",

        Implies(COMP_OCN_OPTION=="SOM", COMP_ICE_OPTION!="PRES") :
           "TODO: remove this relation. Added for testing the logic module.",

        Implies(In(COMP_OCN, ["mom", "pop"]), COMP_ATM!="satm") :
            "If the ocean component is active, then the atmosphere component cannot be made stub.",

        # Assertions that break the logic module
        ###When(COMP_OCN=="docn", COMP_LND_PHYS!="DLND") : "foo",

        # Inter-layer assertions ----------------------------------------------------

        When(COMP_OCN_PHYS=="DOCN", COMP_OCN_OPTION != "(none)"):
            "Must pick a valid DOCN option.",

        When(COMP_ICE_PHYS=="DICE", COMP_ICE_OPTION != "(none)"):
            "Must pick a valid DICE option.",

        When(COMP_ATM_PHYS=="DATM", COMP_ATM_OPTION != "(none)"):
            "Must pick a valid DATM option.",

        When(COMP_ROF_PHYS=="DROF", COMP_ROF_OPTION != "(none)"):
            "Must pick a valid DROF option.",

        When(COMP_WAV_PHYS=="DWAV", COMP_WAV_OPTION != "(none)"):
            "Must pick a valid DWAV option.",

        When(In(COMP_LND, ["clm", "dlnd"]), COMP_LND_OPTION != "(none)"):
            "Must pick a valid LND option.",

        When(COMP_GLC=="cism", COMP_GLC_OPTION != "(none)"):
            "Must pick a valid GLC option.",

        When(And(COMP_ICE=="cice", COMP_OCN == "docn"), COMP_OCN_OPTION=="SOM"):
           "When DOCN is coupled with CICE, DOCN option must be set to SOM.",

        When( Not(And(COMP_LND=="slnd", COMP_ICE=="sice", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc", COMP_WAV=="swav")),
                Not(In(COMP_ATM_OPTION, ["ADIAB", "DABIP04", "TJ16", "HS94", "KESSLER"])) ):
            "Simple CAM physics options can only be picked if all other components are stub.",

        When(COMP_OCN=="mom", In(OCN_GRID, ["tx0.66v1", "gx1v6", "tx0.25v1"])):
            "Not a valid MOM6 grid.",

        When(Contains(COMP_OCN_OPTION, "AQ"), In(OCN_GRID,["0.9x1.25", "1.9x2.5", "4x5"])):
            "When in aquaplanet mode, the ocean grid must be set to f09, f19, or f45",

        When(COMP_OCN!="mom", WAV_GRID != "wtx0.66v1"):
            "wt066v1 wave grid is for MOM6 coupling only",

        When(COMP_ATM_OPTION != "SCAM", ATM_GRID != "T42"):
            "T42 grid can only be used with SCAM option.",

        # Relational assertions for mom6_bathy settings -----------------------------

        Implies(COMP_OCN=="pop", GRID_MODE=="Predefined"):
            "Custom grid mode cannot be selected if the OCN component is POP.",

        Implies(GRID_MODE=="Custom", Or(COMP_OCN=="mom", COMP_LND=="clm")):
            "At least one of OCN and LND must be active when Custom grid mode is selected.",

        Implies(COMP_OCN=="mom", And(OCN_NX>=2, OCN_NY>=2, (OCN_NX*OCN_NY)>=16 )):
            "MOM6 grid dimensions too small.",

        Implies(COMP_OCN=="mom", And(OCN_NX<10000, OCN_NY<10000)):
            "MOM6 grid dimensions too big.",

        Implies(COMP_WAV!="swav", OCN_GRID_EXTENT=="Global"):
            "A regional ocean model cannot be coupled with a wave component.",

        Implies(COMP_ICE!="sice", OCN_GRID_EXTENT=="Global"):
            "A regional ocean model cannot be coupled with an ice component.",

        When(OCN_GRID_EXTENT=="Global", OCN_CYCLIC_X):
            "If custom grid mode is global, the ocean grid must be reentrant in x direction.",

        When(OCN_GRID_EXTENT=="Global", OCN_LENX==360.0 ):
            "OCN grid length in X direction must be set to 360.0 when OCN grid extent is global.",

        When(OCN_GRID_EXTENT=="Global", And(OCN_LENY>0.0, OCN_LENY<=180.0) ):
            "OCN grid length in Y direction must be less than or equal to 180.0 when OCN grid extent is global.",

        When(OCN_GRID_EXTENT=="Regional", Not(OCN_CYCLIC_X)):
            "When a custom regional grid is selected, ocn domain cannot be reentrant (due to an ESMF limitation.)",

        # Relational assertions for custom lnd grid settings -----------------------------

        Implies(And(INITTIME=='HIST', COMP_LND=='clm'), GRID_MODE!="Custom"):
            "When initialization time is set to HIST, cannot create custom clm grids.",

        And(0<=LND_SOIL_COLOR, LND_SOIL_COLOR<=20):
            "Soil color must be set to an integer value between 0 and 20",

        And(0<=LND_SOIL_COLOR, LND_SOIL_COLOR<=20):
            "Soil color must be set to an integer value between 0 and 20",

        LND_DOM_PFT >= 0.0:
            "PFT/CFT must be set to a nonnegative number",

        And(0<=LND_MAX_SAT_AREA, LND_MAX_SAT_AREA<=1):
            "Max fraction of saturated area must be set to a value between 0 and 1.",

        LND_STD_ELEV >= 0.0:
            "Standard deviation of elevation must be a nonnegative number."


    }

    return assertions_dict