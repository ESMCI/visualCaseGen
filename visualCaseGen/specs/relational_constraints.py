from z3 import Implies, And, Or, Not
from ProConPy.csp_utils import In

def get_relational_constraints(cvars):
    """ Returns a dictionary of relational constraints for the given config_vars where keys are the z3 boolean expressions
    and values are error messages to be displayed when the constraint is violated.
    """

    # references to ConfigVars appearing in relational constraints
    INITTIME = cvars['INITTIME']
    COMPSET_MODE = cvars['COMPSET_MODE']
    COMP_ATM = cvars['COMP_ATM'];  COMP_ATM_OPTION = cvars['COMP_ATM_OPTION']
    COMP_LND = cvars['COMP_LND'];  COMP_LND_OPTION = cvars['COMP_LND_OPTION']
    COMP_ICE = cvars['COMP_ICE'];  COMP_ICE_OPTION = cvars['COMP_ICE_OPTION']
    COMP_OCN = cvars['COMP_OCN'];  COMP_OCN_OPTION = cvars['COMP_OCN_OPTION']
    COMP_ROF = cvars['COMP_ROF'];  COMP_ROF_OPTION = cvars['COMP_ROF_OPTION']
    COMP_GLC = cvars['COMP_GLC'];  COMP_GLC_OPTION = cvars['COMP_GLC_OPTION']
    COMP_WAV = cvars['COMP_WAV'];  COMP_WAV_OPTION = cvars['COMP_WAV_OPTION']
    COMP_ATM_PHYS = cvars['COMP_ATM_PHYS']; COMP_LND_PHYS = cvars['COMP_LND_PHYS']
    GRID_MODE = cvars['GRID_MODE']
    ATM_GRID = cvars['ATM_GRID']
    OCN_GRID = cvars['OCN_GRID']
    WAV_GRID = cvars['WAV_GRID']
    ICE_GRID = cvars['ICE_GRID']; ROF_GRID = cvars['ROF_GRID']; GLC_GRID = cvars['GLC_GRID']
    OCN_GRID_MODE = cvars['OCN_GRID_MODE']; OCN_GRID_EXTENT = cvars['OCN_GRID_EXTENT']; OCN_CYCLIC_X = cvars['OCN_CYCLIC_X']
    OCN_NX = cvars['OCN_NX']; OCN_NY = cvars['OCN_NY']; OCN_LENX = cvars['OCN_LENX']; OCN_LENY = cvars['OCN_LENY']
    OCN_IC_MODE = cvars['OCN_IC_MODE']; T_REF = cvars['T_REF']
    LND_GRID_MODE = cvars['LND_GRID_MODE']; LND_SOIL_COLOR = cvars['LND_SOIL_COLOR']; LND_DOM_PFT = cvars['LND_DOM_PFT']
    LND_MAX_SAT_AREA = cvars['LND_MAX_SAT_AREA']; LND_STD_ELEV = cvars['LND_STD_ELEV']
    CUSTOM_ROF_GRID = cvars['CUSTOM_ROF_GRID']
    ROF_OCN_MAPPING_RMAX = cvars['ROF_OCN_MAPPING_RMAX']; ROF_OCN_MAPPING_FOLD = cvars['ROF_OCN_MAPPING_FOLD']

    # DATM modes that force a prognostic land model (CDEPS CLMNCEP datamode family). The remaining DATM modes
    # (NYF, IAF, JRA*) are ocean/sea-ice forcings (CORE2 / JRA55-do), see cdeps/datm/cime_config/config_component.xml.
    DATM_LND_FORCINGS = ["QIA", "WISOQIA", "CRUJRA2024", "CRUJRA2024b", "CRUv7", "GSWP3v1", "NLDAS2", "1PT"]

    # Explicit value lists used instead of z3 string operations (Contains/PrefixOf). The z3 sequence solver becomes
    # extremely slow when many string predicates are combined with the solver's equality assertions, so the rules
    # below enumerate the relevant single-option / grid values instead. Multi-option selections join values with
    # '%'; the few shipped multi-option combinations that matter (CAM7 model-top + chemistry, AIS + GRIS) are listed.
    AQP_MODES = ["SOMAQP", "SST_AQUAP", "AQPFILE", "AQPCONST"] + [f"AQP{i}" for i in range(1, 11)]
    JRA_MODES = ["JRA", "JRA-1p4-2018", "JRA-1p5-2023", "JRA-RYF6162", "JRA-RYF8485", "JRA-RYF9091", "JRA-RYF0304"]
    DROF_JRA_MODES = JRA_MODES + ["JRA-1p4-2018-AIS0ICE", "JRA-1p4-2018-AIS0LIQ", "JRA-1p4-2018-AIS0ROF"]
    DROF_IAF_MODES = ["IAF", "IAFAIS00", "IAFAIS45", "IAFAIS55"]
    CAM7_TOP = ["LT", "MT", "WA", "WX"]
    CAM7_CHEM = ["CSO", "CT0MA", "CT1S1", "CT1S2", "CT1MA", "CT4MA", "CT4S2", "CT4WA"]
    CAM7_TOP_COMBOS = CAM7_TOP + [f"{t}%{c}" for t in CAM7_TOP for c in CAM7_CHEM + ["PORT"]] \
                               + [f"{c}%{t}" for t in CAM7_TOP for c in CAM7_CHEM + ["PORT"]]
    WX_BAD_CHEM = ["CSO", "CT1S1", "CT1S2", "CT4S2"]
    WX_BAD_COMBOS = [f"WX%{c}" for c in WX_BAD_CHEM] + [f"{c}%WX" for c in WX_BAD_CHEM]
    SCAM_IOPS = ["ARM95", "ARM97", "ATEX", "BOMEX", "CGILSS11", "CGILSS12", "CGILSS6", "DYCOMSRF01", "DYCOMSRF02",
                 "GATE3", "MPACE", "RICO", "SPARTICUS", "TOGA2", "TWP06", "CAMFRC"]
    SCAM_MODES = ["SCAM"] + [f"SCAM{iop}" for iop in SCAM_IOPS]
    CROP_MODES = ["BGC-CROP", "BGCDV-CROP", "BGC-CROP-CMIP6DECK", "BGC-CROP-CMIP6WACCMDECK", "NWP-BGC-CROP"]
    AIS_MODES = ["AIS-EVOLVE", "AIS-NOEVOLVE"]; GRIS_MODES = ["GRIS-EVOLVE", "GRIS-NOEVOLVE"]
    BOTH_SHEET_MODES = [f"{a}%{g}" for a in AIS_MODES for g in GRIS_MODES] + [f"{g}%{a}" for a in AIS_MODES for g in GRIS_MODES]
    SE_GRIDS = ["ne3np4", "ne5np4", "ne16np4", "ne30np4", "ne60np4", "ne120np4", "ne240np4",
                "ne3np4.pg2", "ne5np4.pg2", "ne30np4.pg2", "ne60np4.pg2", "ne120np4.pg2", "ne240np4.pg2",
                "ne3np4.pg3", "ne5np4.pg3", "ne16np4.pg3", "ne30np4.pg3", "ne60np4.pg3", "ne120np4.pg3", "ne240np4.pg3",
                "ne5np4.pg4", "ne30np4.pg4", "ne60np4.pg4", "ne120np4.pg4",
                "ne0np4CONUS.ne30x8", "ne0np4TESTONLY.ne5x4", "ne0np4.ARCTIC.ne30x4", "ne0np4.ARCTICGRIS.ne30x8",
                "ne0np4.POLARCAP.ne30x4", "ne0np4.NATL.ne30x8"]
    MPAS_GRIDS = ["mpasa480", "mpasa240", "mpasa120", "mpasa60", "mpasa30", "mpasa15", "mpasa15-3conus", "mpasa7p5", "mpasa3p75"]
    MZ_ROF_GRIDS = ["r05mz", "r05mz_amazon", "HDMAmz_amazon", "USGS_GFmz", "HDMA_CONUSmz", "MERIT_CONUSmz", "MERITmz", "HDMAmz", "HDMA_lake_mz"]

    # Return a dictionary of constraints where keys are the z3 boolean expressions corresponding to the constraints
    # and values are error messages to be displayed when the constraint is violated.
    return {

        Not(And(COMP_ATM=="satm", COMP_LND=="slnd", COMP_ICE=="sice", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc", COMP_WAV=="swav")) :
            "At least one component must be an active or a data model",

        Implies(COMP_OCN=="mom", COMP_WAV!="dwav") :
            "MOM6 cannot be coupled with data wave component.",

        Implies(COMP_ATM=="cam", COMP_ICE!="dice") :
            "CAM cannot be coupled with Data ICE.",

        Implies(COMP_WAV=="ww3", COMP_OCN!="socn") :
            "WW3 can only be selected if an active or data ocean component is present.",

        Implies(Or(COMP_ROF=="rtm", COMP_ROF=="mosart", COMP_ROF=="mizuroute"), COMP_LND=='clm') :
            "Active runoff models can only be selected if CLM is the land component.",

        Implies(And(COMP_OCN=="mom", COMP_ATM=="datm"), COMP_LND=="slnd") :
            "When MOM is coupled with data atmosphere (datm), LND component must be stub (slnd).",

        Implies(And(COMP_ATM=="datm", COMP_LND=="clm"), And(COMP_ICE=="sice", COMP_OCN=="socn")) :
            "If CLM is coupled with DATM, then both ICE and OCN must be stub.",

        Implies(COMP_ATM=="satm", And(COMP_ICE=="sice", COMP_ROF=="srof", COMP_OCN=="socn")) :
            "An active/data atmosphere is needed to force ocean, ice, and/or runoff models.",
        
        Implies(COMP_LND=="slnd", Or(COMP_OCN=="mom", COMP_GLC=="sglc")) :
            "GLC cannot be coupled with a stub land model, unless it is coupled with MOM6.",
        
        Implies(COMP_LND=="slim", And(COMP_GLC=="sglc", COMP_ROF=="srof", COMP_WAV=="swav")) :
            "GLC, ROF, and WAV cannot be coupled with SLIM.",
        
        Implies(COMP_OCN=="socn", COMP_ICE=="sice") :
            "When ocean is made stub, ice must also be stub.",
        
        Implies(COMP_LND=="clm", COMP_ROF!="drof") :
            "CLM cannot be coupled with a data runoff model.",
        
        Implies(COMP_LND=="dlnd", COMP_ATM!="cam") : # TODO: check this constraint.
            "CAM-DLND coupling is not supported.",
        
        Implies(COMP_OCN=="docn", COMP_OCN_OPTION != "(none)"):
            "Must pick a valid DOCN option.",

        Implies(COMP_ICE=="dice", COMP_ICE_OPTION != "(none)"):
            "Must pick a valid DICE option.",

        Implies(COMP_ATM=="datm", COMP_ATM_OPTION != "(none)"):
            "Must pick a valid DATM option.",

        Implies(COMP_ROF=="drof", COMP_ROF_OPTION != "(none)"):
            "Must pick a valid DROF option.",

        Implies(COMP_WAV=="dwav", COMP_WAV_OPTION != "(none)"):
            "Must pick a valid DWAV option.",

        Implies(In(COMP_LND, ["clm", "dlnd"]), COMP_LND_OPTION != "(none)"):
            "Must pick a valid LND option.",

        Implies(COMP_GLC=="cism", COMP_GLC_OPTION != "(none)"):
            "Must pick a valid GLC option.",

        Implies( Not(And(COMP_LND=="slnd", COMP_ICE=="sice", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc", COMP_WAV=="swav")),
                Not(In(COMP_ATM_OPTION, ["ADIAB", "DABIP04", "TJ16", "HS94", "KESSLER", "GRAYRAD"])) ):
            "Simple CAM physics options can only be picked if all other components are stub.",

        # MOM6 only has MOM_input parameter templates for these grids (components/mom/param_templates/MOM_input.yaml);
        # ParamGen yields an unusable MOM_input for any other OCN_GRID.
        Implies(COMP_OCN=="mom", In(OCN_GRID, ["tx2_3v2", "tx2_3v3", "tx2_0v1", "tx0.25v1"])):
            "Not a valid MOM6 grid.",

        Implies(In(COMP_OCN_OPTION, AQP_MODES), In(OCN_GRID,["0.9x1.25", "1.9x2.5", "4x5"])):
            "When in aquaplanet mode, the ocean grid must be set to f09, f19, or f45",

        Implies(COMP_OCN!="mom", WAV_GRID != "wtx0.66v1"):
            "wt066v1 wave grid is for MOM6 coupling only",

        # CAM in CESM3 ships only FV, SE, and MPAS horizontal grids (cam/bld/config_files/horiz_grid.xml); the
        # Gaussian grids below exist for data atmosphere only. cam/bld/configure dies with "no match for dycore".
        Implies(COMP_ATM=="cam", Not(In(ATM_GRID, ["T42", "T5", "T31", "T62", "TL319", "TL639"]))):
            "Gaussian (spectral) grids such as T42, T62, and TL319 are for data atmosphere only; CAM has no such dycore grid.",

        # cam/bld/configure: "SCAM mode only works with SE dycore."
        Implies(In(COMP_ATM_OPTION, SCAM_MODES + ["SCAM%CT1S1"]), In(ATM_GRID, SE_GRIDS)):
            "SCAM (single-column CAM) only works with the spectral element dycore, i.e., an ne* grid.",
        
        Implies(In(COMP_ATM_OPTION, JRA_MODES), ATM_GRID == "TL319"):
            "JRA forcing can only be used with TL319 ATM grid.",
        
        Implies(In(COMP_ATM_OPTION, ["IAF", "NYF"]), ATM_GRID == "T62"):
            "Core2 forcing can only be used with T62 grid.",

        # Additional compset constraints (CESM3 source/doc survey) ------------------

        # cam/cime_config/config_component.xml defines no bare "CAM" physics; the specialized (simple) physics
        # packages are only reachable via their %OPTION.
        Implies(COMP_ATM_PHYS=="Specialized", COMP_ATM_OPTION != "(none)"):
            "A specialized CAM physics package (ADIAB, TJ16, GRAYRAD, HS94, KESSLER) must be selected.",

        # %PORT builds the offline radiation unit driver (-offline_drv rad) instead of the coupled model.
        Implies(In(COMP_ATM_OPTION, ["PORT"] + [f"{t}%PORT" for t in CAM7_TOP] + [f"PORT%{t}" for t in CAM7_TOP]),
                And(COMP_LND=="slnd", COMP_ICE=="sice", COMP_OCN=="socn", COMP_ROF=="srof", COMP_GLC=="sglc", COMP_WAV=="swav")):
            "PORT (offline radiation driver) can only be run with all other components stub.",

        # CAM7 model-top physics (LT: 58 levels, MT: 93, WA: 135, WX: 189) only has initial condition defaults for SE and
        # MPAS grids (cam/bld/namelist_files/namelist_defaults_cam.xml); build-namelist dies on FV grids.
        Implies(And(COMP_ATM_PHYS=="CAM70", In(COMP_ATM_OPTION, CAM7_TOP_COMBOS)), In(ATM_GRID, SE_GRIDS + MPAS_GRIDS)):
            "CAM7 LT/MT/WA/WX physics only have initial conditions for spectral element (ne*) and MPAS grids.",

        # cam/bld/configure: "-chem must be set 'waccm_ma*' with the waccmx option."
        Implies(COMP_ATM_PHYS=="CAM70", Not(In(COMP_ATM_OPTION, WX_BAD_COMBOS))):
            "WACCM-X (WX) requires middle-atmosphere chemistry (CT0MA/CT1MA/CT4MA); tropospheric/specified chemistry is not allowed.",

        # Specified dynamics and nudging use MERRA2 meteorology (1975-2017) and only have HIST_ use cases
        # (cam/cime_config/config_component.xml, use_cases/sd_cam6.xml).
        Implies(In(COMP_ATM_OPTION, ["SDYN", "NUDG"]), INITTIME=="HIST"):
            "Specified dynamics (SDYN) and nudged (NUDG) CAM configurations require the HIST initialization period.",

        # All SCAM IOP compsets are CLM%SP + CICE%PRES + DOCN%DOM + SROF_SGLC_SWAV (cam/cime_config/config_compsets.xml).
        Implies(In(COMP_ATM_OPTION, SCAM_MODES + ["SCAM%CT1S1"]), And(COMP_ROF=="srof", COMP_GLC=="sglc", COMP_WAV=="swav")):
            "SCAM runs a single column: runoff, land ice, and wave components must be stub.",

        # CAM is configured as an aquaplanet only for _SLND_SICE_DOCN%AQP*/%SOMAQP compsets
        # (cam/cime_config/config_component.xml, "-aquaplanet"); the mediator imports nothing from lnd/ice then.
        Implies(In(COMP_OCN_OPTION, AQP_MODES), And(COMP_LND=="slnd", COMP_ICE=="sice", COMP_ROF=="srof")):
            "Aquaplanet data ocean modes require stub land, sea ice, and runoff components.",

        # Prescribed sea ice reads SSTICE_* stream variables that are defined only by DOCN
        # (cice/cime_config/buildnml, cdeps/docn/cime_config/config_component.xml).
        Implies(COMP_ICE_OPTION=="PRES", COMP_OCN=="docn"):
            "Prescribed CICE (%PRES) reads the SST/ice-fraction dataset provided by the data ocean (DOCN) and cannot be used with other ocean components.",

        # F-type configurations: prognostic CICE over prescribed SSTs is unsupported (DiscussCESM FAQ on DOCN-SOM/F compsets).
        Implies(And(COMP_ATM=="cam", COMP_OCN_OPTION=="DOM", COMP_ICE=="cice"), COMP_ICE_OPTION=="PRES"):
            "With CAM and a prescribed-SST data ocean (DOCN%DOM), CICE must run in prescribed mode (%PRES).",

        # The slab ocean needs the ice melt heat flux / frazil feedback from a prognostic ice model
        # (cdeps/docn/docn_datamode_som_mod.F90; "We do not support prescribed ice mode with the DOCN-SOM").
        Implies(COMP_OCN_OPTION=="SOM", And(COMP_ICE!="sice", COMP_ICE_OPTION!="PRES")):
            "The slab ocean model (DOCN%SOM) requires a prognostic (or data) sea ice model; prescribed ice is not supported.",

        # DOCN%IAF maps to datamode "interannual", which cdeps docn does not implement (ocn_comp_nuopc.F90 aborts).
        COMP_OCN_OPTION != "IAF":
            "DOCN%IAF (interannual) is not implemented in CDEPS docn.",

        # DATM%MOSARTTEST has no DATM_MODE mapping (cdeps/datm/cime_config/config_component.xml) and CLM rejects it.
        COMP_ATM_OPTION != "MOSARTTEST":
            "DATM%MOSARTTEST is a test-only forcing with no DATM_MODE mapping.",

        # CLM sets LND_TUNING_MODE from the DATM forcing; NYF/IAF/JRA map to INVALID_DATM_FORCING_FOR_RUNNING_CTSM
        # and other modes have no tuning entry, so CLM build-namelist dies (clm/cime_config/config_component.xml).
        Implies(And(COMP_ATM=="datm", COMP_LND=="clm"), In(COMP_ATM_OPTION, DATM_LND_FORCINGS + ["CPLHIST"])):
            "CLM can only be forced by a land-forcing DATM mode (QIA, CRUJRA2024(b), CRUv7, GSWP3v1, NLDAS2, 1PT, CPLHIST).",

        # LND_TUNING_MODE clm4_5_CRUJRA2024 does not exist (clm/cime_config/config_component.xml valid_values).
        Implies(And(COMP_LND_PHYS=="CLM45", COMP_ATM=="datm"), Not(In(COMP_ATM_OPTION, ["CRUJRA2024", "CRUJRA2024b"]))):
            "CLM4.5 has no tuning mode for CRUJRA2024 forcing; use GSWP3v1 or CRUv7.",

        # Land-forcing DATM datasets provide no ocean fields/coverage; ocean and sea-ice forcing needs CORE2/JRA modes.
        Implies(In(COMP_ATM_OPTION, DATM_LND_FORCINGS), COMP_OCN=="socn"):
            "Land-only DATM forcings (QIA, CRUJRA, CRUv7, GSWP3v1, NLDAS2, 1PT) cannot drive an ocean or sea ice model.",

        # OMIP protocols (CORE-II: Griffies et al. 2016; JRA55-do: Tsujino et al. 2020) and all CESM C/G compsets pair the
        # atmosphere and runoff forcing from the same dataset.
        Implies(And(COMP_ATM=="datm", COMP_ROF=="drof", Not(In(COMP_ROF_OPTION, ["NULL", "GLOFAS", "CPLHIST"]))),
                And(Implies(COMP_ATM_OPTION=="NYF", COMP_ROF_OPTION=="NYF"),
                    Implies(COMP_ATM_OPTION=="IAF", In(COMP_ROF_OPTION, DROF_IAF_MODES)),
                    Implies(In(COMP_ATM_OPTION, JRA_MODES), In(COMP_ROF_OPTION, DROF_JRA_MODES)))):
            "Data atmosphere and data runoff forcings must come from the same dataset family (NYF, IAF, or JRA).",

        # cmeps/cime_config/buildnml selects runseq_D for DATM+CICE+DOCN, which never advances LND, WAV, or GLC.
        Implies(And(COMP_ATM=="datm", COMP_ICE=="cice", COMP_OCN=="docn"), And(COMP_LND=="slnd", COMP_WAV=="swav")):
            "The DATM+CICE+DOCN run sequence never advances land or wave components; they must be stub.",

        # cmeps/cime_config/buildnml selects runseq_TG for DLND+CISM, which runs only LND and GLC.
        Implies(And(COMP_LND=="dlnd", COMP_GLC=="cism"),
                And(COMP_ATM=="satm", COMP_OCN=="socn", COMP_ICE=="sice", COMP_ROF=="srof", COMP_WAV=="swav")):
            "The DLND+CISM (TG) run sequence only advances land and land ice; all other components must be stub.",

        # DLND snow-coupling modes (SCPL/GCPL) are the only ones that export land-ice forcing (cdeps/dlnd).
        Implies(And(COMP_LND=="dlnd", In(COMP_GLC, ["cism", "dglc"])), In(COMP_LND_OPTION, ["SCPL", "GCPL"])):
            "A data land model can only drive a land ice model in snow-coupling mode (SCPL or GCPL).",

        # GLC_TWO_WAY_COUPLING defaults are keyed on "DGLC%" (cmeps config_component_cesm.xml); bare DGLC is never used.
        Implies(COMP_GLC=="dglc", COMP_GLC_OPTION != "(none)"):
            "Must pick a valid DGLC option.",

        # cism/cime_config/buildnml requires exactly one GLC_GRID entry per ice sheet named in the compset (AIS -> ais8,
        # GRIS/EVOLVE/NOEVOLVE -> gris*); multi-sheet grids are written "ais8:gris4".
        Implies(And(COMP_GLC=="cism", In(COMP_GLC_OPTION, AIS_MODES)), GLC_GRID=="ais8"):
            "An Antarctic-only (AIS) CISM configuration requires the ais8 GLC grid.",

        Implies(And(COMP_GLC=="cism", In(COMP_GLC_OPTION, GRIS_MODES + ["EVOLVE", "NOEVOLVE"])), In(GLC_GRID, ["gris4", "gris20"])):
            "A Greenland-only (GRIS, or EVOLVE/NOEVOLVE) CISM configuration requires a gris4 or gris20 GLC grid.",

        Implies(And(COMP_GLC=="cism", In(COMP_GLC_OPTION, BOTH_SHEET_MODES)), GLC_GRID=="ais8:gris4"):
            "Running both ice sheets (AIS and GRIS) requires the two-sheet ais8:gris4 GLC grid.",

        # CTSM: FATES is incompatible with transient land use (flanduse_timeseries) in CLM4.5/CLM5.
        Implies(And(In(COMP_LND_PHYS, ["CLM45", "CLM50"]), In(COMP_LND_OPTION, ["FATES", "FATES-SP"])), INITTIME != "HIST"):
            "FATES with CLM4.5/CLM5 does not support transient (HIST) land use.",

        # CLM_NML_USE_CASE for NOANTHRO only exists for 1850 (clm/cime_config/config_component.xml).
        Implies(In(COMP_LND_OPTION, ["SP-NOANTHRO", "BGC-NOANTHRO"]), INITTIME=="1850"):
            "NOANTHRO (no anthropogenic forcing) CLM configurations are only defined for the 1850 period.",

        # Additional standard-grid constraints ------------------

        # CICE has no grid_file default for tx0.25v1 (cice/cime_config/namelist_definition_cice.xml).
        Implies(COMP_ICE=="cice", ICE_GRID != "tx0.25v1"):
            "CICE has no grid file for the tx0.25v1 ocean/ice grid.",

        # DATM%NLDAS2 covers CONUS only and has start years only for 2000 (cdeps/datm/cime_config/config_component.xml).
        Implies(COMP_ATM_OPTION=="NLDAS2", And(INITTIME=="2000", In(ATM_GRID, ["0.125nldas2", "CLM_USRDAT"]))):
            "NLDAS2 forcing is a regional CONUS dataset: it requires the 0.125nldas2 (or CLM_USRDAT) grid and the 2000 period.",

        # DATM%1PT streams exist only for three single-point tower grids and CLM_USRDAT (cdeps/datm stream definitions).
        Implies(COMP_ATM_OPTION=="1PT", In(ATM_GRID, ["1x1_mexicocityMEX", "1x1_vancouverCAN", "1x1_urbanc_alpha", "CLM_USRDAT"])):
            "1PT tower forcing is only available for 1x1_mexicocityMEX, 1x1_vancouverCAN, 1x1_urbanc_alpha, and CLM_USRDAT grids.",

        # CLMBuildNamelist.pm: these single-point grids "must use a compset with CN and CROP turned on".
        Implies(In(ATM_GRID, ["1x1_smallvilleIA", "1x1_cidadinhoBR", "1x1_numaIA"]), In(COMP_LND_OPTION, CROP_MODES)):
            "The 1x1_smallvilleIA, 1x1_cidadinhoBR, and 1x1_numaIA grids require a BGC-CROP land configuration.",

        # Runoff grids per model (mosart/rtm/mizuRoute buildnml direction-file tables; rx1/JRA025/GLOFAS are DROF-only).
        # A "null" runoff grid switches an active runoff model into NULL mode, which is allowed.
        Implies(COMP_ROF=="mosart", In(ROF_GRID, ["r05", "r8th", "0.125nldas2", "null"])):
            "MOSART only has routing input for the r05, r8th, and 0.125nldas2 runoff grids.",

        Implies(COMP_ROF=="rtm", In(ROF_GRID, ["r05", "r01", "null"])):
            "RTM only has routing input for the r05 and r01 runoff grids.",

        Implies(COMP_ROF=="mizuroute", In(ROF_GRID, MZ_ROF_GRIDS + ["null"])):
            "mizuRoute requires one of the mizuRoute (*mz) runoff grids.",

        Implies(In(ROF_GRID, ["rx1", "JRA025", "JRA025v2", "GLOFAS"]), In(COMP_ROF, ["drof", "srof"])):
            "The rx1, JRA025, and GLOFAS runoff grids are data runoff (DROF) grids and cannot be used with an active runoff model.",

        # mom6_forge-related constraints ------------------
        Implies(And(COMP_OCN=="mom", COMP_LND=="slnd", COMP_ICE=="sice"), OCN_LENY<180.0):
            "If LND and ICE are stub, custom MOM6 grid must exclude poles (singularity).",

        Implies(And(COMP_OCN != "mom", COMP_LND!="clm"), GRID_MODE=="Standard"):
            "Custom grids can only be generated when MOM6 and/or CLM are selected.",

        Implies(COMP_OCN!="mom", OCN_GRID_MODE=="Standard"):
            "Custom OCN grids can only be generated for MOM6.",
    
         #todo OCN_GRID_MODE!="Modify Existing":
         #todo     "This feature (Modify Existing) not implemented yet.",

        And(OCN_NX>=2, OCN_NY>=2, (OCN_NX*OCN_NY)>=16 ):
            "MOM6 grid dimensions too small.",

        And(OCN_NX<10000, OCN_NY<10000):
            "MOM6 grid dimensions too big.",
        
        Implies(OCN_GRID_EXTENT=="Regional", OCN_CYCLIC_X=="False"):
            "Regional ocean domain cannot be reentrant (due to an ESMF limitation.)",

        Implies(OCN_GRID_EXTENT=="Global", OCN_CYCLIC_X=="True"):
            "Global ocean domains must be reentrant in the x-direction.",

        Implies(OCN_GRID_EXTENT=="Global", OCN_LENX==360.0):
            "Global ocean model domains must have a length of 360 degrees in the x-direction.",

        And(OCN_LENY>0.0, OCN_LENY<=180.0):
            "OCN grid length in Y direction must be <= 180.0.",
        
        And(OCN_LENX>0.0, OCN_LENX<=360.0):
            "OCN grid length in X direction must be <= 360.0.",

        Implies(OCN_IC_MODE=="Simple", And(T_REF>=-2.0, T_REF<=40.0)):
            "Reference temperature must be between -2 and 40 degrees Celsius.",

        # Custom lnd grid constraints ------------------
        Implies(COMP_LND!="clm", LND_GRID_MODE=="Standard"):
            "Custom LND grids can only be generated for CLM.",

        And(0<=LND_SOIL_COLOR, LND_SOIL_COLOR<=20):
            "Soil color must be set to an integer value between 0 and 20",

        LND_DOM_PFT >= 0.0:
            "PFT/CFT must be set to a nonnegative number",

        LND_DOM_PFT <= 78:
            "PFT/CFT index cannot exceed 78 (the last crop functional type).",

        And(0<=LND_MAX_SAT_AREA, LND_MAX_SAT_AREA<=1):
            "Max fraction of saturated area must be set to a value between 0 and 1.",

        LND_STD_ELEV >= 0.0:
            "Standard deviation of elevation must be a nonnegative number.",

        # Custom rof grid constraints ------------------
        Implies(In(CUSTOM_ROF_GRID, ["JRA025", "rx1"]), COMP_ROF=="drof"):
            "JRA025 and rx1 runoff grids can only be selected if DROF is the runoff component.",

        CUSTOM_ROF_GRID != "r05mz": # mizuroute is no longer available
            "r05mz runoff grid can only be selected if MIZUROUTE is the runoff component.",
        
        In(COMP_ROF_OPTION, ["NYF", "IAF"]) == (CUSTOM_ROF_GRID=="rx1"):
            "When Core2 forcing is selected for the ocean component, the runoff grid must be set to rx1.",

        In(COMP_ROF_OPTION, DROF_JRA_MODES) == (CUSTOM_ROF_GRID == "JRA025"):
            "When JRA forcing is selected for the ocean component, the runoff grid must be set to JRA025.",

        (COMP_ROF_OPTION == "GLOFAS") == (CUSTOM_ROF_GRID=="GLOFAS"):
            "When GLOFAS forcing is selected for the ocean component, the runoff grid must be set to GLOFAS.",

        ROF_OCN_MAPPING_RMAX > 0:
            "ROF_OCN_MAPPING_RMAX must be a positive number.",
        
        ROF_OCN_MAPPING_FOLD > 0:
            "ROF_OCN_MAPPING_FOLD must be a positive number.",

        ROF_OCN_MAPPING_RMAX <= 4000:
            "ROF_OCN_MAPPING_RMAX must be less than or equal to 4000 km.",
        
        ROF_OCN_MAPPING_FOLD <= 8000:
            "ROF_OCN_MAPPING_FOLD must be less than or equal to 8000 km.",

        #### Assertions to stress-test the CSP solver

        ### Implies(COMP_OCN=="docn", COMP_LND_PHYS!="DLND") : "FOO",

        ### Implies(COMP_OCN=="docn", COMP_ATM_PHYS!="CAM60") : "BAR",

        ### Not(In(COMP_LND_PHYS, ['CLM45', 'CLM50'])) : "BAZ",

    }