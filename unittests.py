#!/usr/bin/env python3

import unittest
import sys
from contextlib import contextmanager
from io import StringIO
import logging
import ipywidgets as widgets


from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.gui_create_custom import GUI_create_custom
from visualCaseGen.config_var_str import ConfigVarStr
from cli import cmdCaseGen

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
        self.assertEqual(ConfigVarStr.vdict['COMP_ATM_PHYS'].options, None)
        self.assertEqual(ConfigVarStr.vdict['COMP_ATM_OPTION'].options, None)

        # now set COMP_OCN and others successfully
        cmd.onecmd("COMP_OCN =mom")
        cmd.onecmd("COMP_LND = clm")
        cmd.onecmd("COMP_ATM= cam")

        # After having set COMP_ATM, confirm COMP_ATM_PHYS and COMP_ATM_OPTION are updated.
        self.assertIn("CAM60", ConfigVarStr.vdict['COMP_ATM_PHYS'].options, None)
        self.assertIn("1PCT", ConfigVarStr.vdict['COMP_ATM_OPTION'].options, None)

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
        ConfigVarStr.vdict['COMP_ATM'].widget = widgets.ToggleButtons()
        ConfigVarStr.vdict['COMP_ICE'].widget = widgets.ToggleButtons()
        ConfigVarStr.vdict['COMP_OCN'].widget = widgets.ToggleButtons()
        ConfigVarStr.vdict['COMP_LND'].widget = widgets.ToggleButtons()
        ConfigVarStr.vdict['COMP_ROF'].widget = widgets.ToggleButtons()
        ConfigVarStr.vdict['COMP_GLC'].widget = widgets.ToggleButtons()
        ConfigVarStr.vdict['COMP_WAV'].widget = widgets.ToggleButtons()

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


    def test_D_gui_sequence(self):
        """Test GUI by checking an assignment sequence that was previously causing an error."""
        if 'D' in tests_to_skip:
            return

        GUI_create_custom(ci).construct()

        COMP_ATM = ConfigVarStr.vdict['COMP_ATM']
        COMP_LND = ConfigVarStr.vdict['COMP_LND']
        COMP_ICE = ConfigVarStr.vdict['COMP_ICE']
        COMP_OCN = ConfigVarStr.vdict['COMP_OCN']
        COMP_ROF = ConfigVarStr.vdict['COMP_ROF']
        COMP_GLC = ConfigVarStr.vdict['COMP_GLC']
        COMP_WAV = ConfigVarStr.vdict['COMP_WAV']

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

        #todo COMP_ICE.value = 'dice'
        #todo COMP_ICE.value = 'sice'
        #todo COMP_ICE.value = 'dice'

    def test_E_gui_random(self):
        """Test GUI by randomly assigning component values many times"""
        if 'E' in tests_to_skip:
            return

        import random
        from visualCaseGen.config_var_str import ConfigVarStr
        #from visualCaseGen.logic import profiler
        #import cProfile, pstats

        for i in range(2):
            GUI_create_custom(ci).construct()

            COMP_ATM = ConfigVarStr.vdict['COMP_ATM']
            COMP_LND = ConfigVarStr.vdict['COMP_LND']
            COMP_ICE = ConfigVarStr.vdict['COMP_ICE']
            COMP_OCN = ConfigVarStr.vdict['COMP_OCN']
            COMP_ROF = ConfigVarStr.vdict['COMP_ROF']
            COMP_GLC = ConfigVarStr.vdict['COMP_GLC']
            COMP_WAV = ConfigVarStr.vdict['COMP_WAV']

            random.seed(10) # to get consistent performance metrics

            N = 50
            # first try setting to valid options only
            for i in range(N):
                comp = random.choice([COMP_ATM, COMP_LND, COMP_ICE, COMP_OCN, COMP_ROF, COMP_GLC, COMP_WAV])
                valid_opts = [opt for opt in comp.options if comp._options_validities[opt] is True]
                if len(valid_opts)>0:
                    random_opt = random.choice(valid_opts)
                    #print(i, comp.name, random_opt)
                    comp.value = random_opt
                else:
                    print("WARNING: encountered cases where there is no valid opt for "+comp.name)

            # not set to any values including invalid ones
            for i in range(N):
                comp = random.choice([COMP_ATM, COMP_LND, COMP_ICE, COMP_OCN, COMP_ROF, COMP_GLC, COMP_WAV])
                try:
                    comp.value = random.choice(comp.options)
                except AssertionError:
                    pass

        #stats = pstats.Stats(profiler).sort_stats('time')
        #stats.print_stats()

    def test_F_var_assignment(self):
        """Check constraint hypergraph generator."""
        if 'F' in tests_to_skip:
            return

        cmd = cmdCaseGen(exit_on_error=False)
        cmd.onecmd("chg")

if __name__ == '__main__':
    tests_to_skip = ''
    #tests_to_skip = 'F'
    #tests_to_skip = 'ABCDE'
    logging.getLogger().setLevel(logging.ERROR)
    unittest.main()