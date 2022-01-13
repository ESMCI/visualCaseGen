#!/usr/bin/env python3

import logging
import os, sys
import cmd
import re
import readline

pth = os.path.dirname(os.path.dirname(os.path.dirname(os.path.join(os.path.abspath(__file__)))))
sys.path.append(pth)

logger = logging.getLogger("cmdCaseGen")

from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.config_var import ConfigVar
from visualCaseGen.config_var_opt import ConfigVarOpt
from visualCaseGen.config_var_opt_ms import ConfigVarOptMS
import visualCaseGen.logic_engine as logic
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

    constraints = {

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

    return constraints

class cmdCaseGen(cmd.Cmd):

    intro = "\nWelcome to the cmdCaseGen command shell. Type help or ? to list commands."
    prompt = "(cmd) "
    file = None

    def __init__(self, exit_on_error=False):
        cmd.Cmd.__init__(self)
        logic.reset()
        ConfigVar.reset()
        self.ci = CIME_interface("nuopc")
        self._init_configvars()
        self._init_options()
        self._exit_on_error = exit_on_error
        logic.add_relational_assertions(relational_assertions_setter)

    def printError(self, msg):
        if self._exit_on_error:
            sys.exit("ERROR: "+msg)
        else:
            logger.error(msg)

    def _init_configvars(self):

        ConfigVar.compliances = self.ci.compliances

        cv_inittime = ConfigVarOpt('INITTIME')
        for comp_class in self.ci.comp_classes:
            ConfigVarOpt('COMP_'+str(comp_class))
            ConfigVarOpt('COMP_{}_PHYS'.format(comp_class), never_unset=True)
            ConfigVarOptMS('COMP_{}_OPTION'.format(comp_class), never_unset=True)
            ConfigVar('{}_GRID'.format(comp_class))
        ConfigVar('MASK_GRID')
        ConfigVar('COMPSET')
        ConfigVarOpt('GRID')

    def _init_options(self):
        ConfigVarOpt.vdict['INITTIME'].options = ['1850', '2000', 'HIST']
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar.vdict['COMP_{}'.format(comp_class)]
            cv_comp.options = [model for model in  self.ci.models[comp_class] if model[0] != 'x']

    def do_vars(self, arg):
        """
        vars: list assigned ConfigVars.
        vars -a: list all ConfigVars."""
        if arg in ['-a', 'a', '-all', 'all']:
            # list all variables
            for var in ConfigVar.vdict:
                val = ConfigVar.vdict[var].value
                print("{}={}".format(var,val))
        else:
            # list set variables only
            for var in ConfigVar.vdict:
                val = ConfigVar.vdict[var].value
                if val:
                    print("{}={}".format(var,val))

    def completenames(self, text, *ignored):
        """ This gets called when a (partial or full) single word, i.e., param name,
        is to be completed. """
        complete_list = []
        for varname in ConfigVar.vdict:
            if varname.startswith(text.strip()):
                complete_list.append(varname)
        return complete_list

    def completedefault(self, text, line, begidx, endidx):
        """ This completion method gets called when more than one words are already typed,
        i.e., when a parameter assignment is to be made."""
        if '=' in line:
            sline = line.split('=')
            varname = sline[0].strip()
            if ConfigVar.exists(varname):
                var = ConfigVar.vdict[varname]
                assert isinstance(var,ConfigVarOpt) or isinstance(var,ConfigVarOptMS)
                options_sans_validity = var._options_sans_validity()
                val_begin = sline[1].strip()
                if len(val_begin)>0:
                    return [opt for opt in options_sans_validity if opt.startswith(val_begin)]
                else:
                    return options_sans_validity
        return []


    def _assign_var(self, varname, val):
        try:
            var = ConfigVar.vdict[varname]
            var.value = val
        except Exception as e:
            self.printError("{}".format(e))

    def default(self, line):
        """The default user input is variable assignment, i.e., key=value where key is a ConfigVar name
        and value is a valid value for the ConfigVar. If no value is provided, current value is printed."""

        # assign variable value
        if re.search(r'\b\w+\b *= *\b\w+\b', line):
            sline = line.split('=')
            varname = sline[0].strip()
            if ConfigVar.exists(varname):
                val = sline[1].strip()
                self._assign_var(varname, val)
            else:
                self.printError("Cannot find the variable {}. To list all variables, type: vars -a".format(varname))

        # query variable value
        elif re.search(r'^ *\b\w+ *$', line):
            varname = line.strip()
            if ConfigVar.exists(varname):
                val = ConfigVar.vdict[varname].value
                print("{}".format(val))
            else:
                self.printError("{} is not a variable name or a command".format(varname))
        else:
            self.printError("Unknown syntax! Provide a key=value pair where key is a ConfigVar, e.g., COMP_OCN")

    def do_assertions(self, line):
        """list all assertions"""
        print(logic.universal_solver().assertions())

    def close(self):
        if self.file:
            self.file.close()
            self.file = None

    def do_exit(self, arg):
        """Close the command line interface."""
        print('Closing cmdCaseGen command shell')
        self.close()
        return True

    def do_x(self, arg):
        """Close the command line interface."""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Close the command line interface."""
        return self.do_exit(arg)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.WARNING)
    cmdCaseGen().cmdloop()

