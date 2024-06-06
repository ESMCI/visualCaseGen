from ProConPy.config_var import ConfigVar, cvars
from ProConPy.stage import Stage
from ProConPy.csp_solver import csp
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.initialize_configvars import initialize_configvars
from visualCaseGen.initialize_widgets import initialize_widgets
from visualCaseGen.initialize_stages import initialize_stages
from visualCaseGen.specs.options import set_options
from visualCaseGen.specs.relational_constraints import get_relational_constraints

import networkx as nx
from networkx.drawing.nx_pydot import graphviz_layout
import matplotlib.pyplot as plt


def initialize(cime):
    """Initializes visualCaseGen"""
    ConfigVar.reboot()
    Stage.reboot()
    initialize_configvars(cime)
    initialize_widgets(cime)
    initialize_stages(cime)
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())


def gen_stage_tree(stage):
    """Generate the stage tree by traversing all stages using depth-first search.

    Parameters
    ----------
    stage : Stage
        The initial stage to start the traversal from.

    Returns
    -------
    G : nx.DiGraph
        The directed graph representing the stage tree.
    """

    # Instantiate a graph object that will represent the stage tree
    G = nx.Graph()

    while (next := stage.get_next(full_dfs=True)) is not None:
        if stage._parent is not None and stage._parent.has_condition():
            G.add_edge(stage._parent, stage)
        for child in stage._children:
            G.add_edge(stage, child)
        stage = next
    
    assert nx.is_forest(G), "The stage tree is not a tree."
    
    return G

def plot_stage_tree(stage):
    """Plot the stage tree."""

    # Traverse the stage tree using depth-first search
    G = gen_stage_tree(stage)

    # Draw the graph
    try:
        from networkx.drawing.nx_pydot import graphviz_layout

        pos = graphviz_layout(G, prog="dot")
    except ImportError:
        print(
            "WARNING: PyGraphviz is not installed. Drawing the graph using spring layout."
        )
        pos = nx.spring_layout(G)
    nx.draw(
        G,
        pos,
        with_labels=False,
        edge_color="gray",
        node_color="powderblue",
        font_size=9,
    )
    text = nx.draw_networkx_labels(G, pos)
    for _, t in text.items():
        t.set_rotation(20)
        t.set_verticalalignment("center")

    # Set the color of Guard nodes
    guard_nodes = [node for node in G.nodes if node.has_condition()]
    nx.draw_networkx_nodes(G, pos, nodelist=guard_nodes, node_color="wheat")

    plt.show()


def main():
    initialize(CIME_interface())
    plot_stage_tree(Stage.first())


if __name__ == "__main__":
    main()
