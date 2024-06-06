from tools.stage_tree_plotter import initialize, gen_stage_tree
from tools.stage_pipeline_plotter import gen_stage_pipeline
from ProConPy.stage import Stage
from visualCaseGen.cime_interface import CIME_interface

def test_stage_pipeline():
    """Confirm that the stage pipeline is a directed acyclic graph."""
    cime = CIME_interface()
    initialize(cime)

    # The below call will raise an assertion error if the stage tree is not a forest
    gen_stage_tree(Stage.first())

    # The below call will raise an assertion error if the stage tree is not a directed acyclic graph
    gen_stage_pipeline(Stage.first())

