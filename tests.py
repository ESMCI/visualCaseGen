#!/usr/bin/env python3

from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.initialize_configvars import initialize_configvars
from visualCaseGen.initialize_widgets import initialize_widgets
from visualCaseGen.initialize_stages import initialize_stages
from visualCaseGen.specs.options import set_options
from visualCaseGen.specs.relational_constraints import get_relational_constraints
from ProConPy.csp_solver import csp
from ProConPy.hgraph_utils import plot_nxgraph

cime = CIME_interface()
#owh.set_verbosity(verbose=True) # TODO: remove
initialize_configvars(cime)
initialize_widgets(cime) 
initialize_stages(cime) 
set_options(cime)
csp.initialize(cvars, get_relational_constraints(cvars))

plot_nxgraph(csp.hgraph)

print(csp._initialized)