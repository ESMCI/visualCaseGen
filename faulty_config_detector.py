from visualCaseGen.config_var import ConfigVar, cvars
from visualCaseGen.config_var_str import ConfigVarStr
from visualCaseGen.config_var_str_ms import ConfigVarStrMS
from visualCaseGen.config_var_compset import ConfigVarCompset
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.logic_utils import When
from specs.relational_assertions import relational_assertions_setter
from specs.options_specs import OptionsSpec, get_options_specs
from z3 import Solver, Implies, And, sat, unsat, Not, unknown, simplify
from z3 import z3util
import subprocess
import os, shutil
from multiprocessing import Pool, Process, Array, Queue, current_process

ci = CIME_interface("nuopc")
testroot = "/glade/scratch/altuntas/vcg/"

def init_configvars():

    ConfigVarStr('INITTIME')
    for comp_class in ci.comp_classes:
        ConfigVarStr('COMP_'+str(comp_class))
        ConfigVarStr('COMP_{}_PHYS'.format(comp_class), always_set=True)
        ConfigVarStrMS('COMP_{}_OPTION'.format(comp_class), always_set=True)
        ConfigVarStr('{}_GRID'.format(comp_class))
    ConfigVarCompset("COMPSET", always_set=True)
    ConfigVarStr('MASK_GRID')
    cv_grid = ConfigVarStrMS('GRID')


def test_compset(compset_and_grid):

    compset = compset_and_grid[0]
    grid_alias = compset_and_grid[1]
    pid = current_process().pid
    msg = "-------------------------------------------------------------------\n"
    msg += f"{pid}: Checking compset {compset} with grid {grid_alias}\n"

    cmd = f"{ci.cimeroot}/scripts/create_test SMS_Lm0.{grid_alias}.{compset}.cheyenne_intel --no-run --test-root {testroot} --output-root {testroot}"

    timeout = False
    returncode = -1
    stdout = ""
    try:
        runout = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
        returncode = runout.returncode
        stdout = runout.stdout.decode('UTF-8')
    except subprocess.TimeoutExpired:
        timeout = True

    if timeout or returncode == 0:
        if timeout:
            msg += f"{pid:}        SUCCESS (timeout)\n"
        else:
            msg += f"{pid:}        SUCCESS\n"

        # remove the test dir
        try:
            for line in stdout.split('\n'):
                if line.startswith("Creating"):
                    testdir = line.split()[-1]
                    shutil.rmtree(testdir)
        except:
            pass

    else:
        err_msg = stdout
        try:
            err_msg = err_msg.split("Errors were:")[1]
            err_msg = err_msg.split("Waiting for tests")[0] 
        except IndexError:
            pass
        msg += f"{pid}: FATAL {err_msg}\n"
    
    print(msg)

def find_a_grid(s, compset):

    # Add grid options assertion
    s.push()

    GRID = cvars['GRID'] 
    grid_opt_assertions = OptionsSpec.get_options_assertions(GRID)
    for asrt in grid_opt_assertions:
        s.add(asrt)

    grid_alias = None
    if s.check() == sat:
        grid_alias = s.model()[GRID]
    else:
        raise RuntimeError(f"Couldn't find a grid for {compset}")
    s.pop()

    return grid_alias

def traverse_configs(f, k):
    # based on z3util.get_models

    s = Solver()
    s.add(f)

    buffer_size = 18
    processes = []

    compsets_and_grids = []
    i = 0
    while s.check() == sat and i < k:
        i = i + 1
        m = s.model()
        if not m:  # if m == []
            break
        new_compset = m[cvars['COMPSET']].sexpr()
        grid_alias = find_a_grid(s,new_compset).sexpr()
        compsets_and_grids.append((new_compset,grid_alias))

        if len(compsets_and_grids) == buffer_size:
            if len(processes)>0:
                for p in processes:
                    p.join()
            processes = [Process(target=test_compset, args=(compsets_and_grids[i],)) for i in range(buffer_size)]
            for p in processes:
                p.start()
            compsets_and_grids = []

        # create new constraint to block the current model
        block = Not(And([v() == m[v] for v in m]))
        ###block = Not(And([cvars[f"COMP_{comp_class}_PHYS"] == m[cvars[f"COMP_{comp_class}_PHYS"]] for comp_class in ci.comp_classes]) )
        s.add(block)

    for p in processes: 
        if p.is_alive():
            p.join()

    if s.check() == unknown:
        return None
    elif s.check() == unsat and i == 0:
        return False
    else:
        return 1

def main():
    print("Running visualCaseGen faulty config detector")
    init_configvars()

    # Static Solver
    s = Solver()

    # Add relational assertions
    relational_assertions_dict = relational_assertions_setter(cvars)
    relational_assertions_list = list(relational_assertions_dict.keys())
    for asrt in relational_assertions_list:
        if isinstance(asrt, When):
            s.add(Implies(asrt.antecedent, asrt.consequent))
        else:
            s.add(asrt)


    # Add options (domain) specifications
    get_options_specs(cvars, ci)
    for varname, var in cvars.items():
        if varname == "GRID":
            # grid assertions will be added later on (for each compset, after the compset is determined)
            continue
        if hasattr(var, 'options_spec'):
            assertions = OptionsSpec.get_options_assertions(var)
            for asrt in assertions:
                s.add(asrt)


    # narrow down the search to simpler models configs:
    s.add(cvars['INITTIME'] == "2000")
    s.add(cvars['COMP_OCN'] != "pop")
    s.add(cvars['COMP_WAV'] != "ww3dev")

    # Check that assertions are satisfiable
    assert s.check() == sat

    comp_atm_option = cvars['COMP_ATM_OPTION']
    comp_atm_option_opts = OptionsSpec.get_options(comp_atm_option)
    comp_lnd_option = cvars['COMP_LND_OPTION']
    comp_lnd_option_opts = OptionsSpec.get_options(comp_lnd_option)
    comp_ice_option = cvars['COMP_ICE_OPTION']
    comp_ice_option_opts = OptionsSpec.get_options(comp_ice_option)

    #for atm_option in comp_atm_option_opts:
    for lnd_option in comp_lnd_option_opts: 
        for ice_option in comp_ice_option_opts: 
            s.push()
            #s.add([comp_atm_option==atm_option, comp_lnd_option==lnd_option, comp_ice_option==ice_option])
            s.add([comp_lnd_option==lnd_option, comp_ice_option==ice_option])
            if s.check() == sat:
                traverse_configs(And(s.assertions()), 18)
            s.pop()
            break # todoooooooooooooooooooooooo removeooooooooooooooooooooooooooo
        break


if __name__ == '__main__':
    main()