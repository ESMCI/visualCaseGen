
from visualCaseGen.logic_engine import In
from z3 import * # this is only needed for constraint setter functions

def relational_assertions_setter(lvars):

    COMP_ATM = lvars['COMP_ATM']
    COMP_LND = lvars['COMP_LND']
    COMP_ICE = lvars['COMP_ICE']
    COMP_OCN = lvars['COMP_OCN']
    COMP_ROF = lvars['COMP_ROF']
    COMP_GLC = lvars['COMP_GLC']
    COMP_WAV = lvars['COMP_WAV']

    assertions_dict = {

        Implies(COMP_ICE=="sice", And(COMP_LND=="slnd", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc") ) : 
            "If COMP_ICE is stub, all other components must be stub (except for ATM)",

        Implies(COMP_OCN=="mom", COMP_WAV!="dwav") :
            "MOM6 cannot be coupled with data wave component.",

        Implies(COMP_ATM=="cam", COMP_ICE!="dice") :
            "CAM cannot be coupled with Data ICE",

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
        
    }

    return assertions_dict