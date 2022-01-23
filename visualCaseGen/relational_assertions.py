from z3 import Implies, And, Or

# Auxiliary definitions of logic expression shorthands
def In(var, value_list):
    """Expression to check whether the value of a variable is in a given list."""
    return Or([var==value for value in value_list])

def relational_assertions_setter(cvars):

    COMP_ATM = cvars['COMP_ATM'];  COMP_ATM_PHYS = cvars['COMP_ATM_PHYS'];  COMP_ATM_OPTION = cvars['COMP_ATM_OPTION']
    COMP_LND = cvars['COMP_LND'];  COMP_LND_PHYS = cvars['COMP_LND_PHYS'];  COMP_LND_OPTION = cvars['COMP_LND_OPTION']
    COMP_ICE = cvars['COMP_ICE'];  COMP_ICE_PHYS = cvars['COMP_ICE_PHYS'];  COMP_ICE_OPTION = cvars['COMP_ICE_OPTION']
    COMP_OCN = cvars['COMP_OCN'];  COMP_OCN_PHYS = cvars['COMP_OCN_PHYS'];  COMP_OCN_OPTION = cvars['COMP_OCN_OPTION']
    COMP_ROF = cvars['COMP_ROF'];  COMP_ROF_PHYS = cvars['COMP_ROF_PHYS'];  COMP_ROF_OPTION = cvars['COMP_ROF_OPTION']
    COMP_GLC = cvars['COMP_GLC'];  COMP_GLC_PHYS = cvars['COMP_GLC_PHYS'];  COMP_GLC_OPTION = cvars['COMP_GLC_OPTION']
    COMP_WAV = cvars['COMP_WAV'];  COMP_WAV_PHYS = cvars['COMP_WAV_PHYS'];  COMP_WAV_OPTION = cvars['COMP_WAV_OPTION']

    assertions_dict = {

        Implies(COMP_ICE=="sice", And(COMP_LND=="slnd", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc") ) : 
            "If COMP_ICE is stub, all other components must be stub (except for ATM)",

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

        Implies(COMP_OCN=="mom", Or(COMP_LND!="slnd", COMP_ICE!="sice")) :
             "LND or ICE must be present to hide MOM6 grid poles.",

        Implies(And(COMP_ATM=="datm", COMP_LND=="clm"), And(COMP_ICE=="sice", COMP_OCN=="socn")) :
            "If CLM is coupled with DATM, then both ICE and OCN must be stub.",
        
        Implies(In(COMP_ATM_OPTION, ["ADIAB", "DABIP04", "TJ16", "HS94", "KESSLER"]), 
            And(COMP_LND=="slnd", COMP_ICE=="sice", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc", COMP_WAV=="swav") ):
            "When a simple CAM physics option is picked, all other components must be stub.",
        
        #todo Implies(And(COMP_ICE=="cice", COMP_OCN == "docn"), COMP_OCN_OPTION=="SOM"):
        #todo    "When DOCN is coupled with CICE, DOCN option must be set to SOM."

        Implies(COMP_ICE=="dice", COMP_ICE_OPTION != "(none)"):
            "Must pick a valid DICE option.",
        
        Implies(COMP_ATM=="datm", COMP_ATM_OPTION != "(none)"):
            "Must pick a valid DATM option.",
        
        Implies(COMP_ROF=="drof", COMP_ROF_OPTION != "(none)"):
            "Must pick a valid DROF option.",
        
        Implies(COMP_WAV=="dwav", COMP_WAV_OPTION != "(none)"):
            "Must pick a valid DWAV option.",
        
        Implies(COMP_LND=="clm", COMP_LND_OPTION != "(none)"):
            "Must pick a valid CLM option.",
        
        Implies(COMP_GLC=="cism", COMP_GLC_OPTION != "(none)"):
            "Must pick a valid GLC option.",
        
    }

    return assertions_dict