#!/usr/bin/env python3

import unittest
import sys
from cli import cmdCaseGen
from contextlib import contextmanager
from io import StringIO
import logging

logger = logging.getLogger("unittests")

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

    def test_var_assignment(self):
        """Check several simple variable assignments."""

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

        # now set COMP_OCN and others successfully
        cmd.onecmd("COMP_OCN =mom")
        cmd.onecmd("COMP_ATM= cam")
        cmd.onecmd("COMP_LND = clm")

        #capture another syntax error:
        with self.assertLogs() as captured:
            cmd.onecmd("COMP _OCN = 'pop'")
        self.assertEqual(captured.records[0].getMessage(),
            'Unknown syntax! Provide a key=value pair where key is a ConfigVarStr, e.g., COMP_OCN' )
        
        # confirm the above assignment failure didn't change the previous value of COMP_OCN
        with self.captured_output() as (out, err):
            cmd.onecmd("COMP_OCN")
        self.assertEqual(out.getvalue().strip(), "mom")

    def test_relational_assertions(self):
        """Test several relational assignments defined in relational assertions.py"""

        # Set COMP_OCN to mom and then try setting COMP_WAV to dwav, which should fail
        cmd = cmdCaseGen(exit_on_error=False)
        cmd.onecmd("COMP_OCN = mom")
        with self.assertLogs() as captured:
            cmd.onecmd("COMP_WAV = dwav")
        self.assertEqual(captured.records[0].getMessage(),
            'COMP_WAV=dwav violates assertion:"MOM6 cannot be coupled with data wave component."' )

        # instead set COMP_WAC to ww3
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

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.ERROR)
    unittest.main()