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
from visualCaseGen.config_var_base import ConfigVarBase
from visualCaseGen.config_var_str import ConfigVarStr
from visualCaseGen.relational_assertions import relational_assertions_setter
import visualCaseGen.logic_engine as logic

class cmdCaseGen(cmd.Cmd):

    intro = "\nWelcome to the cmdCaseGen command shell. Type help or ? to list commands."
    prompt = ">>> "
    file = None

    def __init__(self, exit_on_error=False):
        cmd.Cmd.__init__(self)
        ConfigVarBase.reset()
        self.ci = CIME_interface("nuopc")
        self._init_configvars()
        self._init_options()
        self._exit_on_error = exit_on_error
        ConfigVarBase.add_relational_assertions(relational_assertions_setter)

    def printError(self, msg):
        if self._exit_on_error:
            sys.exit("ERROR: "+msg)
        else:
            logger.error(msg)

    def _init_configvars(self):

        cv_inittime = ConfigVarStr('INITTIME')
        for comp_class in self.ci.comp_classes:
            ConfigVarStr('COMP_'+str(comp_class))
            ConfigVarStr('COMP_{}_PHYS'.format(comp_class), always_set=True)
            ConfigVarStr('COMP_{}_OPTION'.format(comp_class), always_set=True)
            ConfigVarStr('{}_GRID'.format(comp_class))
        ConfigVarStr('MASK_GRID')
        ConfigVarStr('COMPSET')
        ConfigVarStr('GRID')

    def _init_options(self):
        ConfigVarStr.vdict['INITTIME'].options = ['1850', '2000', 'HIST']
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVarStr.vdict['COMP_{}'.format(comp_class)]
            cv_comp.options = [model for model in  self.ci.models[comp_class] if model[0] != 'x']

    def do_vars(self, arg):
        """
        vars: list assigned ConfigVars.
        vars -a: list all ConfigVars."""
        if arg in ['-a', 'a', '-all', 'all']:
            # list all variables
            for varname, var in ConfigVarStr.vdict.items():
                print("{}={}".format(varname,var.value))
        else:
            # list set variables only
            for varname, var in ConfigVarStr.vdict.items():
                if not var.is_none():
                    print("{}={}".format(varname,var.value))

    def completenames(self, text, *ignored):
        """ This gets called when a (partial or full) single word, i.e., param name,
        is to be completed. """
        complete_list = []
        for varname in ConfigVarStr.vdict:
            if varname.startswith(text.strip()):
                complete_list.append(varname)
        return complete_list

    def completedefault(self, text, line, begidx, endidx):
        """ This completion method gets called when more than one words are already typed,
        i.e., when a parameter assignment is to be made."""
        if '=' in line:
            sline = line.split('=')
            varname = sline[0].strip()
            if ConfigVarStr.exists(varname):
                var = ConfigVarStr.vdict[varname]
                assert var.has_options()
                options = var.options
                val_begin = sline[1].strip()
                if len(val_begin)>0:
                    return [opt for opt in options if opt.startswith(val_begin)]
                else:
                    return options
        return []


    def _assign_var(self, varname, val):
        try:
            var = ConfigVarStr.vdict[varname]
            var.value = val
        except Exception as e:
            self.printError("{}".format(e))

    def default(self, line):
        """The default user input is variable assignment, i.e., key=value where key is a ConfigVarStr name
        and value is a valid value for the ConfigVarStr. If no value is provided, current value is printed."""

        # assign variable value
        if re.search(r'\b\w+\b *= *\b\w+\b', line):
            sline = line.split('=')
            varname = sline[0].strip()
            if ConfigVarStr.exists(varname):
                val = sline[1].strip()
                self._assign_var(varname, val)
            else:
                self.printError("Cannot find the variable {}. To list all variables, type: vars -a".format(varname))

        # query variable value
        elif re.search(r'^ *\b\w+ *$', line):
            varname = line.strip()
            if ConfigVarStr.exists(varname):
                val = ConfigVarStr.vdict[varname].value
                print("{}".format(val))
            else:
                self.printError("{} is not a variable name or a command".format(varname))
        else:
            self.printError("Unknown syntax! Provide a key=value pair where key is a ConfigVarStr, e.g., COMP_OCN")

    def do_assertions(self, line):
        """list all assertions"""
        print(logic.universal_solver().assertions())

    def do_opts(self, line):
        """For a given varname, print all options and their validities"""
        varname = line.strip()
        if not re.search(r'^\b\w+\b$', varname):
            self.printError("Invalid syntax for the opts command. Provide a variable name.")
            return
        var = ConfigVarStr.vdict[varname]
        if var.has_options():
            for opt in var._widget.options:
                print('\t', opt)
        else:
            printError("Variable {} doesn't have options".format(varname))

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
    logging.getLogger().setLevel(logging.ERROR)
    cmdCaseGen().cmdloop()

