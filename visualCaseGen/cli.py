import logging
import argparse
import os, sys
import cmd
import re
import readline

pth = os.path.dirname(os.path.dirname(os.path.dirname(os.path.join(os.path.abspath(__file__)))))
sys.path.append(pth)

logger = logging.getLogger("cmdCaseGen")

from .cime_interface import CIME_interface
from .config_var import ConfigVar

parser = argparse.ArgumentParser(description='cmdCaseGen command line interface')
parser.add_argument('-d', '--driver', choices=['nuopc', 'mct'], default="nuopc", type=str)

args = parser.parse_args()


class cmdCaseGen(cmd.Cmd):

    intro = "\nWelcome to the cmdCaseGen command shell. Type help or ? to list commands."
    prompt = "(cmd) "
    file = None

    def __init__(self, driver, exit_on_error=False):
        cmd.Cmd.__init__(self)
        ConfigVar.reset()
        self.ci = CIME_interface(driver)
        self._init_configvars()
        self._init_options()
        self._exit_on_error = exit_on_error

    def printError(self, msg):
        if self._exit_on_error:
            sys.exit("ERROR: "+msg)
        else:
            logger.error(msg)

    def _init_configvars(self):

        ConfigVar.compliances = self.ci.compliances

        cv_inittime = ConfigVar('INITTIME')
        for comp_class in self.ci.comp_classes:
            cv_comp = ConfigVar('COMP_'+str(comp_class))
            cv_comp_phys = ConfigVar('COMP_{}_PHYS'.format(comp_class), never_unset=True)
            cv_comp_option = ConfigVar('COMP_{}_OPTION'.format(comp_class), never_unset=True)
            cv_comp_grid = ConfigVar('{}_GRID'.format(comp_class))
        cv_compset = ConfigVar('COMPSET')
        cv_grid = ConfigVar('GRID')
        cv_casename = ConfigVar('CASENAME')

    def _init_options(self):
        pass
        #ConfigVar['INITTIME'].options = ['1850', '2000', 'HIST']


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
        complete_list = []
        for varname in ConfigVar.vdict:
            if varname.startswith(text.strip()):
                complete_list.append(varname)
        return complete_list

    def completedefault(self, text, line, begidx, endidx):
        if '=' in line:
            sline = line.split('=')
            varname = sline[0].strip()
            if ConfigVar.exists(varname):
                val_begin = sline[1].strip()
                if val_begin:
                    return [opt for opt in ConfigVar.vdict[varname].options if opt.startswith(val_begin)]
                else:
                    return ConfigVar.vdict[varname].options
        return []


    def default(self, line):
        """The default user input is variable assignment, i.e., key=value where key is a ConfigVar name
        and value is a valid value for the ConfigVar."""
        if re.search(r'\b\w+\b *= *\b\w+\b', line):
            # key=value pair, i.e., an assignment
            sline = line.split('=')
            varname = sline[0].strip()
            if ConfigVar.exists(varname):
                val = sline[1].strip()
                try:
                    ConfigVar.vdict[varname].value = val
                except Exception as e:
                    self.printError("{}".format(e))
            else:
                self.printError("Cannot find the variable {}. To list all variables, type: ls -a".format(varname))
        elif re.search(r'^ *\b\w+ *$', line):
            # single word, i.e., a value inquiry
            varname = line.strip()
            if ConfigVar.exists(varname):
                val = ConfigVar.vdict[varname].value
                #print("{} = {}".format(varname,val))
                print("{}".format(val))
            else:
                self.printError("{} is not a variable name or a command".format(varname))
        else:
            self.printError("Unknown syntax! Provide a key=value pair where key is a ConfigVar, e.g., COMP_OCN")

    def do_assertions(self, line):
        """assertions [VARNAME]: list all assertions of the given variable [VARNAME]"""
        if not re.search(r'^ *\b\w+ *$', line.strip()):
            self.printError("Must provide a variable name.")
            return
        varname = line.strip()
        if ConfigVar.exists(varname):
            print(ConfigVar.vdict[varname].assertions)
        else:
            self.printError("{} not a valid variable name".format(varname))

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
    cmdCaseGen(args.driver).cmdloop()

