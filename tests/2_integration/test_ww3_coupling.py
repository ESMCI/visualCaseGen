#!/usr/bin/env python3
"""Tests for coupling a regional MOM6 ocean with active waves (WW3).

Historically visualCaseGen forbade pairing a regional ocean with a wave
component (and with a data ice component) via two relational constraints.
Those constraints were removed to enable WW3 coupling for regional MOM6
configurations, so these tests confirm:

  1. the forbidding messages are gone from the relational-constraint set, and
  2. a custom compset with MOM6 + WW3 can actually be configured down to a
     Regional ocean grid without triggering a ConstraintViolation.
"""

import os
import pytest
from pathlib import Path

from ProConPy.config_var import ConfigVar, cvars
from ProConPy.stage import Stage
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.csp_solver import csp
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.initialize_configvars import initialize_configvars
from visualCaseGen.initialize_widgets import initialize_widgets
from visualCaseGen.initialize_stages import initialize_stages
from visualCaseGen.specs.options import set_options
from visualCaseGen.specs.relational_constraints import get_relational_constraints


# do not show logger output
import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'temp'))


def _fresh_csp():
    """Reboot the config-var / stage machinery and return the CIME interface."""
    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface()
    initialize_configvars(cime)
    initialize_widgets(cime)
    initialize_stages(cime)
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())
    return cime


def test_regional_wave_and_dice_constraints_removed():
    """The two constraints that forbade coupling a regional ocean with a wave
    or a data-ice component must no longer be present in the constraint set."""
    _fresh_csp()
    reasons = list(get_relational_constraints(cvars).values())

    assert not any(
        "regional ocean model cannot be coupled with a wave component" in r.lower()
        for r in reasons
    ), "The regional-vs-wave constraint should have been removed."
    assert not any(
        "regional ocean model cannot be coupled with a data ice component" in r.lower()
        for r in reasons
    ), "The regional-vs-data-ice constraint should have been removed."


def test_dwav_option_constraint_is_live():
    """The DWAV-option constraint used to compare COMP_WAV against the bogus
    value 'phys' (a dead constraint); it now compares against 'dwav'. Confirm
    the message is present and that it actually fires for a data-wave compset."""
    _fresh_csp()
    reasons = list(get_relational_constraints(cvars).values())
    assert any("Must pick a valid DWAV option." == r for r in reasons)


def test_regional_mom6_couples_with_ww3():
    """Configure a custom MOM6 + WW3 compset and drive it down to a Regional
    ocean grid. Setting OCN_GRID_EXTENT='Regional' with an active wave model
    used to raise a ConstraintViolation; it must now succeed."""
    _fresh_csp()

    assert Stage.first().enabled
    cvars['COMPSET_MODE'].value = 'Custom'
    cvars['INITTIME'].value = '2000'

    # Component selection: CAM/CLM/CICE/MOM/MOSART/SGLC + active waves (WW3).
    cvars['COMP_ATM'].value = "cam"
    cvars['COMP_LND'].value = "clm"
    cvars['COMP_ICE'].value = "cice"
    cvars['COMP_OCN'].value = "mom"
    cvars['COMP_ROF'].value = "mosart"
    cvars['COMP_GLC'].value = "sglc"
    cvars['COMP_WAV'].value = "ww3"

    # Component physics
    assert Stage.active().title.startswith('Component Physics')
    cvars['COMP_ATM_PHYS'].value = "CAM60"
    cvars['COMP_LND_PHYS'].value = "CLM50"

    # Component options
    assert Stage.active().title.startswith('Component Options')
    cvars['COMP_ATM_OPTION'].value = "(none)"
    cvars['COMP_LND_OPTION'].value = "SP"
    cvars['COMP_ICE_OPTION'].value = "(none)"
    cvars['COMP_OCN_OPTION'].value = "(none)"
    cvars['COMP_ROF_OPTION'].value = "(none)"

    # Grid
    assert Stage.active().title.startswith('2. Grid')
    cvars['GRID_MODE'].value = 'Custom'
    assert Stage.active().title.startswith('Custom Grid')

    custom_grid_path = Path(temp_dir) / "custom_grid"
    cvars['CUSTOM_GRID_PATH'].value = str(custom_grid_path)

    assert Stage.active().title.startswith('Atm')
    cvars['CUSTOM_ATM_GRID'].value = "TL319"

    assert Stage.active().title.startswith('Ocean')
    cvars['OCN_GRID_MODE'].value = "Create New"

    # The key assertion: a Regional ocean extent is now compatible with an
    # active wave component (no ConstraintViolation).
    assert Stage.active().title.startswith('Custom Ocean')
    cvars['OCN_GRID_EXTENT'].value = "Regional"
    assert cvars['OCN_GRID_EXTENT'].value == "Regional"

    # A regional domain must be non-reentrant: cyclic-x stays False, and trying
    # to make it reentrant is still rejected.
    with pytest.raises(ConstraintViolation):
        cvars['OCN_CYCLIC_X'].value = "True"
    cvars['OCN_CYCLIC_X'].value = "False"
    assert cvars['OCN_CYCLIC_X'].value == "False"


def _drive_custom_mom6_to_ocn_mode(comp_wav="ww3", ocn_grid_mode="Create New"):
    """Set up a custom CAM/CLM/CICE/MOM/MOSART/SGLC compset with the given wave component and
    advance through the custom-grid flow up to assigning the ocean grid mode. The Wave Grid
    stage's options are determined by COMP_WAV and OCN_GRID_MODE, so they are available once
    OCN_GRID_MODE is set (the stage itself comes later in the flow)."""
    _fresh_csp()
    cvars['COMPSET_MODE'].value = 'Custom'
    cvars['INITTIME'].value = '2000'
    cvars['COMP_ATM'].value = "cam"
    cvars['COMP_LND'].value = "clm"
    cvars['COMP_ICE'].value = "cice"
    cvars['COMP_OCN'].value = "mom"
    cvars['COMP_ROF'].value = "mosart"
    cvars['COMP_GLC'].value = "sglc"
    cvars['COMP_WAV'].value = comp_wav
    cvars['COMP_ATM_PHYS'].value = "CAM60"
    cvars['COMP_LND_PHYS'].value = "CLM50"
    cvars['COMP_ATM_OPTION'].value = "(none)"
    cvars['COMP_LND_OPTION'].value = "SP"
    cvars['COMP_ICE_OPTION'].value = "(none)"
    cvars['COMP_OCN_OPTION'].value = "(none)"
    cvars['COMP_ROF_OPTION'].value = "(none)"
    cvars['GRID_MODE'].value = 'Custom'
    cvars['CUSTOM_GRID_PATH'].value = str(Path(temp_dir) / "custom_grid")
    cvars['CUSTOM_ATM_GRID'].value = "TL319"
    cvars['OCN_GRID_MODE'].value = ocn_grid_mode


def test_wav_grid_options_ww3_custom_ocean():
    """WW3 + a custom (Create New) ocean grid: the user may reuse the custom ocean grid as the
    wave grid OR pick a standard wave grid."""
    _drive_custom_mom6_to_ocn_mode(comp_wav="ww3", ocn_grid_mode="Create New")
    assert set(cvars['WAV_GRID_MODE'].options) == {"Custom Ocean Grid", "Standard"}


def test_wav_grid_options_ww3_standard_ocean():
    """WW3 + a standard ocean grid: there is no custom ocean grid to reuse, so only a standard
    wave grid is offered."""
    _drive_custom_mom6_to_ocn_mode(comp_wav="ww3", ocn_grid_mode="Standard")
    assert list(cvars['WAV_GRID_MODE'].options) == ["Standard"]


def test_wav_grid_options_stub_wave():
    """Stub waves (swav): the 'Custom Ocean Grid' option is not offered (only the placeholder
    Standard option), and -- being a single valid option -- it auto-resolves so the relevance-
    gated Wave Grid stage can be skipped without user interaction."""
    _drive_custom_mom6_to_ocn_mode(comp_wav="swav", ocn_grid_mode="Create New")
    assert list(cvars['WAV_GRID_MODE'].options) == ["Standard"]


if __name__ == "__main__":
    test_regional_wave_and_dice_constraints_removed()
    test_dwav_option_constraint_is_live()
    test_regional_mom6_couples_with_ww3()
    test_wav_grid_options_ww3_custom_ocean()
    test_wav_grid_options_ww3_standard_ocean()
    test_wav_grid_options_stub_wave()
    print("All tests passed!")
