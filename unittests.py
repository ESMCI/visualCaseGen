#!/usr/bin/env python3

import unittest
import os
import sys
import shutil
import logging
import ipywidgets as widgets
import subprocess
from io import StringIO
from getpass import getuser
from contextlib import contextmanager

from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.gui_create_custom import GUI_create_custom
from visualCaseGen.gui_create_predefined import GUI_create_predefined
from visualCaseGen.config_var import cvars
from visualCaseGen.create_case_widget import CreateCaseWidget
from specs.options_specs import OptionsSpec, get_options_specs
from cli import cmdCaseGen

import argparse
parser = argparse.ArgumentParser(description="visualCaseGen unit and integration tests")
parser.add_argument('-a', action='store_true', help='run the full test suite.')
parser.add_argument('-t', metavar='tcode', type=str, required=False,
                    help='Run given test codes only. For example, to run test A and C only: -t AC ')
parser.add_argument('-chg', action='store_true', help='construct the constraint hypergraph only')
args = parser.parse_args()

logger = logging.getLogger("unittests")

ci = CIME_interface("nuopc")

class TestParamGen(unittest.TestCase):
    """ A unit test class for visualCaseGen. """

    @contextmanager
    def captured_output(self):
        """ A context manager to capture the output of cmd onecmd calls. The captured
        outputs are then compared with expected results. """
        new_out, new_err = StringIO(), StringIO()
        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = new_out, new_err
            yield sys.stdout, sys.stderr
        finally:
            sys.stdout, sys.stderr = old_out, old_err

    def test_A_var_assignment(self):
        """Check several simple variable assignments."""
        if 'A' in tests_to_skip:
            return

        cmd = cmdCaseGen(exit_on_error=False)

        # set INITTIME to 1850 and confirm assignment
        cmd.onecmd("INITTIME=1850")
        with self.captured_output() as (out, err):
            cmd.onecmd("INITTIME")
        self.assertEqual(out.getvalue().strip(), "1850")

        # Overwrite INITTIME
        cmd.onecmd("INITTIME = HIST")
        with self.captured_output() as (out, err):
            cmd.onecmd("INITTIME")
        self.assertEqual(out.getvalue().strip(), "HIST")

        # set INITTIME to an invalid option and confirm error log
        with self.assertLogs() as captured:
            cmd.onecmd("INITTIME=1849")
        self.assertEqual(captured.records[0].getMessage(),
            '1849 not an option for INITTIME' )

        # do not enclose string within quotes
        with self.assertLogs() as captured:
            cmd.onecmd("COMP_OCN = 'mom'")
        self.assertEqual(captured.records[0].getMessage(),
            'Unknown syntax! Provide a key=value pair where key is a ConfigVarStr, e.g., COMP_OCN' )

        # confirm the above assignment was not successful
        with self.captured_output() as (out, err):
            cmd.onecmd("COMP_OCN")
        self.assertEqual(out.getvalue().strip(), "None")

        # confirm COMP_ATM_PHYS and COMP_ATM_OPTION are initially empty
        self.assertEqual(cvars['COMP_ATM_PHYS'].options, [])
        self.assertEqual(cvars['COMP_ATM_OPTION'].options, [])

        # now set COMP_OCN and others successfully
        cmd.onecmd("COMP_OCN =mom")
        cmd.onecmd("COMP_LND = clm")
        cmd.onecmd("COMP_ATM= cam")

        # After having set COMP_ATM, confirm COMP_ATM_PHYS and COMP_ATM_OPTION are updated.
        self.assertIn("CAM60", cvars['COMP_ATM_PHYS'].options)
        self.assertIn("1PCT", cvars['COMP_ATM_OPTION'].options)

        #capture another syntax error:
        with self.assertLogs() as captured:
            cmd.onecmd("COMP _OCN = 'pop'")
        self.assertEqual(captured.records[0].getMessage(),
            'Unknown syntax! Provide a key=value pair where key is a ConfigVarStr, e.g., COMP_OCN' )

        # confirm the above assignment failure didn't change the previous value of COMP_OCN
        with self.captured_output() as (out, err):
            cmd.onecmd("COMP_OCN")
        self.assertEqual(out.getvalue().strip(), "mom")

    def test_B_relational_assertions(self):
        if 'B' in tests_to_skip:
            return
        """Test several relational assignments defined in relational assertions.py"""

        # Set COMP_OCN to mom and then try setting COMP_WAV to dwav, which should fail
        cmd = cmdCaseGen(exit_on_error=False)
        cmd.onecmd("COMP_OCN = mom")
        with self.assertLogs() as captured:
            cmd.onecmd("COMP_WAV = dwav")
        self.assertEqual(captured.records[0].getMessage(),
            'COMP_WAV=dwav violates assertion:"MOM6 cannot be coupled with data wave component."' )

        # instead set COMP_WAV to ww3
        cmd.onecmd("COMP_WAV=ww3")
        with self.captured_output() as (out, err):
            cmd.onecmd("COMP_WAV")
        self.assertEqual(out.getvalue().strip(), "ww3")

        # Set COMP_ATM to datm and then try setting COMP_LND to dlnd, which should fail since COMP_OCN=mom
        cmd.onecmd("COMP_ATM=datm")
        with self.assertLogs() as captured:
            cmd.onecmd("COMP_LND = dlnd")
        self.assertEqual(captured.records[0].getMessage(),
            'COMP_LND=dlnd violates assertion:"When MOM|POP is forced with DATM, LND must be stub."' )

        # Re-assign COMP and check if we can set COMP_ICE to dice
        cmd.onecmd("COMP_ATM = cam")
        with self.assertLogs() as captured:
            cmd.onecmd("COMP_ICE = dice")
        self.assertEqual(captured.records[0].getMessage(),
            'COMP_ICE=dice violates assertion:"CAM cannot be coupled with Data ICE."' )

        # Check opposite of the implication above:
        cmd.onecmd("COMP_ATM = datm")
        cmd.onecmd("COMP_ICE = dice")
        with self.assertLogs() as captured:
            cmd.onecmd("COMP_ATM = cam")
        self.assertEqual(captured.records[0].getMessage(),
            'COMP_ATM=cam violates assertion:"CAM cannot be coupled with Data ICE."' )

    def test_C_widget_assignment(self):
        """Test assignment of widgets of ConfigVars"""
        if 'C' in tests_to_skip:
            return

        cmd = cmdCaseGen(exit_on_error=False)
        cvars['COMP_ATM'].widget = widgets.ToggleButtons()
        cvars['COMP_ICE'].widget = widgets.ToggleButtons()
        cvars['COMP_OCN'].widget = widgets.ToggleButtons()
        cvars['COMP_LND'].widget = widgets.ToggleButtons()
        cvars['COMP_ROF'].widget = widgets.ToggleButtons()
        cvars['COMP_GLC'].widget = widgets.ToggleButtons()
        cvars['COMP_WAV'].widget = widgets.ToggleButtons()

        # Re-assign COMP and check if we can set COMP_ICE to dice
        cmd.onecmd("COMP_ATM = cam")
        with self.assertLogs() as captured:
            cmd.onecmd("COMP_ICE = dice")
        self.assertEqual(captured.records[0].getMessage(),
            'COMP_ICE=dice violates assertion:"CAM cannot be coupled with Data ICE."' )

        # Check opposite of the implication above:
        cmd.onecmd("COMP_ATM = datm")
        cmd.onecmd("COMP_ICE = dice")
        with self.assertLogs() as captured:
            cmd.onecmd("COMP_ATM = cam")
        self.assertEqual(captured.records[0].getMessage(),
            'COMP_ATM=cam violates assertion:"CAM cannot be coupled with Data ICE."' )

        with self.assertLogs() as captured:
            cmd.onecmd("COMP_ROF = rtm")
        self.assertTrue(
            '' in captured.records[0].getMessage() and
            'If running with RTM|MOSART, CLM must be selected as the land component.' in captured.records[0].getMessage() and
            'Asrt.3' not in captured.records[0].getMessage()
        )
        with self.assertLogs() as captured:
            cmd.onecmd("COMP_ROF = rtm")
        self.assertTrue(
            'If CLM is coupled with DATM, then both ICE and OCN must be stub.' in captured.records[0].getMessage() and
            'If running with RTM|MOSART, CLM must be selected as the land component.' in captured.records[0].getMessage() and
            'Asrt.3' not in captured.records[0].getMessage()
        )

        cmd.onecmd("COMP_OCN = docn")
        with self.assertLogs() as captured:
            cmd.onecmd("COMP_LND = clm")
        self.assertEqual(captured.records[0].getMessage(),
            'COMP_LND=clm violates assertion:"If CLM is coupled with DATM, then both ICE and OCN must be stub."' )

    def test_D_gui_predefined(self):
        """Test GUI predefined mode."""
        if 'D' in tests_to_skip:
            return

        GUI_create_predefined(ci).construct()
        cvars['COMP_ATM_FILTER'].value = "cam"
        cvars['COMP_OCN_FILTER'].value = "mom"
        cvars['COMPSET'].value = cvars['COMPSET'].options[0]
        cvars['GRID'].value = "f09_t061"

        if ci.machine == "cheyenne" and getuser()=="altuntas":
            casepath = "/glade/scratch/altuntas/TEMP.visualCaseGen_test.001"
            if os.path.exists(casepath):
                shutil.rmtree(casepath)

            cmd = "{}/scripts/create_newcase --res {} --compset {} --case {} --machine {} --run-unsupported".format(
                ci.cimeroot,
                cvars['GRID'].value,
                cvars['COMPSET'].value.split(':')[0],
                casepath,
                ci.machine)
            runout = subprocess.run(cmd, shell=True, capture_output=True)
            if runout.returncode == 0:
                print("\nSUCCESS: Case created at {}.\nNow removing this temporary case...".format(casepath))
                shutil.rmtree(casepath)
            else:
                print(runout.stdout)
                print("ERROR: {} ".format(runout.stderr))


    def test_E_gui_custom_sequence(self):
        """Test GUI by checking assignment sequences that were previously causing issues."""
        if 'E' in tests_to_skip:
            return

        GUI_create_custom(ci).construct()

        COMP_ATM = cvars['COMP_ATM']
        COMP_LND = cvars['COMP_LND']
        COMP_ICE = cvars['COMP_ICE']
        COMP_OCN = cvars['COMP_OCN']
        COMP_ROF = cvars['COMP_ROF']
        COMP_GLC = cvars['COMP_GLC']
        COMP_WAV = cvars['COMP_WAV']
        COMP_OCN_PHYS = cvars['COMP_OCN_PHYS']
        COMP_OCN_OPTION = cvars['COMP_OCN_OPTION']

        # first check an assignment sequence that was causing an error:
        COMP_OCN.value = 'docn'
        COMP_ROF.value = 'mosart'
        with self.captured_output() as (out, err):
            try:
                COMP_ATM.value = 'datm'
            except AssertionError as e:
                print(e)
        self.assertTrue(
            'If CLM is coupled with DATM, then both ICE and OCN must be stub.' in out.getvalue().strip() and
            'If running with RTM|MOSART, CLM must be selected as the land component.' in out.getvalue().strip() and
            'Asrt.3' not in out.getvalue().strip()
        )

        # After having set COMP_OCN, confirm COMP_OCN_PHYS and COMP_OCN_OPTION are updated.
        self.assertIn("DOCN", COMP_OCN_PHYS.options)
        self.assertIn("DOM", COMP_OCN_OPTION.options)

        COMP_OCN.value = 'docn'
        COMP_OCN.value = 'socn'
        COMP_OCN.value = 'docn'

        # make sure that dependent variable override feature works by setting COMP_ICE to CICE,
        # which should change the value of COMP_OCN_OPTION implicitly due to a preconditioned relation.
        self.assertEqual(COMP_OCN_OPTION.value, "DOM")
        COMP_ICE.value = 'cice'
        self.assertEqual(COMP_OCN_OPTION.value, "SOM")

    def test_F_gui_custom_random(self):
        """Test GUI (custom mode) by randomly assigning component values many times"""
        if 'F' in tests_to_skip:
            return

        import random
        from visualCaseGen.dev_utils import profiler
        import pstats


        N = 40; seeds = [8]
        if args.a is True:
            N = 60; seeds = [8, 10, 13, 20]

        #profiler.enable()

        for sd in seeds:
            print("seed:", sd)
            random.seed(sd) # to get consistent performance metrics and reproducibility, use the same set of seeds all the time

            GUI_create_custom(ci).construct()
            COMP_ATM = cvars['COMP_ATM']
            COMP_LND = cvars['COMP_LND']
            COMP_ICE = cvars['COMP_ICE']
            COMP_OCN = cvars['COMP_OCN']
            COMP_ROF = cvars['COMP_ROF']
            COMP_GLC = cvars['COMP_GLC']
            COMP_WAV = cvars['COMP_WAV']
            comp_list = [COMP_ATM, COMP_LND, COMP_ICE, COMP_OCN, COMP_ROF, COMP_GLC, COMP_WAV]

            # first try setting to valid options only
            for i in range(N):
                comp = random.choice(comp_list)
                valid_opts = [opt for opt in comp.options if comp._options_validities[opt] is True]
                if len(valid_opts)>0:
                    random_opt = random.choice(valid_opts)
                    comp.value = random_opt
                else:
                    print("WARNING: encountered cases where there is no valid opt for "+comp.name+", seed: "+str(sd))

            # now set to any values including invalid ones
            for i in range(N):
                comp = random.choice(comp_list)
                try:
                    comp.value = random.choice(comp.options)
                except AssertionError:
                    pass

            # now set component physics and options:
            comp_list_determined = [comp for comp in comp_list if comp.value is not None]
            for i in range(N):
                comp = random.choice(comp_list_determined)
                comp_phys = cvars['{}_PHYS'.format(comp.name)]
                comp_opt = cvars['{}_OPTION'.format(comp.name)]

                # Phys
                valid_opts = [opt for opt in comp_phys.options if comp_phys._options_validities[opt] is True]
                if len(valid_opts)>0:
                    random_opt = random.choice(valid_opts)
                    comp_phys.value = random_opt
                else:
                    print("WARNING: encountered cases where there is no valid opt for "+comp_phys.name+", seed: "+str(sd))

                # Options
                valid_opts = [opt for opt in comp_opt.options if comp_opt._options_validities[opt] is True]
                if len(valid_opts)>0:
                    random_opt = random.choice(valid_opts)
                    comp_opt.value = random_opt
                else:
                    print("WARNING: encountered cases where there is no valid opt for "+comp_opt.name+", seed: "+str(sd))

            # more shuffling of options:
            for i in range(N):
                comp = random.choice(comp_list_determined)
                comp_opt = cvars['{}_OPTION'.format(comp.name)]

                # Options
                valid_opts = [opt for opt in comp_opt.options if comp_opt._options_validities[opt] is True]
                if len(valid_opts)>0:
                    random_opt = random.choice(valid_opts)
                    comp_opt.value = random_opt
                else:
                    print("WARNING: encountered cases where there is no valid opt for "+comp_opt.name+", seed: "+str(sd))

        #profiler.disable()

        #stats = pstats.Stats(profiler).sort_stats(pstats.SortKey.CUMULATIVE)
        #stats.print_stats(30)

    def test_G_chg(self):
        """Check constraint hypergraph generator."""
        if 'G' in tests_to_skip:
            return

        cmd = cmdCaseGen(exit_on_error=False)
        cmd.onecmd("chg")

    def test_H_options_specs(self):
        if 'H' in tests_to_skip:
            return

        GUI_create_custom(ci).construct()
        get_options_specs(cvars, ci)
        OptionsSpec.write_all_options_specs(cvars, 'log_opts_specs.txt')

if __name__ == '__main__':
    tests_to_skip = ''
    if args.chg is True:
        tests_to_skip = 'ABCDEFH'
    if args.t is not None:
        assert len(args.t)>0
        tests_to_skip = ''.join([c for c in 'ABCDEFGH' if c not in args.t])
    logging.getLogger().setLevel(logging.ERROR)
    unittest.main(argv=['-q'])