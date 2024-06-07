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
import matplotlib.pyplot as plt
from networkx.drawing.nx_pydot import graphviz_layout


def initialize(cime):
    """Initializes visualCaseGen"""
    ConfigVar.reboot()
    Stage.reboot()
    initialize_configvars(cime)
    initialize_widgets(cime)
    initialize_stages(cime)
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())


def gen_cgraph():
    """Generates the constraint graph based on relational constraints and dependent variables."""

    G = nx.DiGraph()
    for _, cvar in cvars.items():
        for related_var in csp._cgraph[cvar]:
            G.add_edge(cvar, related_var)
        for dependent_var in cvar._dependent_vars:
            G.add_edge(cvar, dependent_var)

    # TODO: remove this manual addition and make sure it is added automatically.
    G.add_edge(cvars["COMPSET_ALIAS"], cvars["COMPSET_LNAME"])

    return G


def plot_cgraph():
    """Plots the constraint graph."""

    G = gen_cgraph()
    pos = graphviz_layout(G, prog="sfdp")
    nx.draw(
        G,
        pos,
        with_labels=False,
        node_size=100,
        node_color="skyblue",
        font_color="black",
        edge_color="gray",
        linewidths=0.5,
        width=0.5,
        alpha=0.5,
    )

    text = nx.draw_networkx_labels(G, pos)
    for _, t in text.items():
        # t.set_rotation(20)
        # t.set_verticalalignment("center_baseline")
        t.set_fontsize(8)

    plt.show()


def main():
    initialize(CIME_interface())
    plot_cgraph()


if __name__ == "__main__":
    main()
