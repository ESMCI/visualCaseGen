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
import os


light_color = "sandybrown"
dark_color = "sienna"
highlight_color = "tomato"

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
    plt.figure(figsize=(10, 5))

    nx.draw(
        G,
        pos,
        with_labels=False,
        node_size=100,
        node_color=light_color,
        font_color="black",
        edge_color="gray",
        linewidths=0.5,
        width=0.5,
        alpha=0.7,
    )

    text = nx.draw_networkx_labels(G, pos)
    for _, t in text.items():
        # t.set_rotation(20)
        # t.set_verticalalignment("center_baseline")
        t.set_fontsize(9)

    #plt.show()
    plt.savefig('cgraph.png')

def animate_graph_traversal(traversal_list):
    """Animates the graph traversal and saves the frames as png files."""
    G = gen_cgraph()
    pos = graphviz_layout(G, prog="sfdp")
    fig, ax = plt.subplots()
    frames = []

    plt.figure(figsize=(10, 5))

    for i, node in enumerate(traversal_list):
        nx.draw(
            G,
            pos,
            with_labels=False,
            node_size=100,
            node_color=light_color,
            font_color="black",
            edge_color="gray",
            linewidths=0.5,
            width=0.5,
            alpha=0.7,
        )
        visited_nodes = set(traversal_list[:i+1])
        text = nx.draw_networkx_labels(G, pos, labels={node: node if node in visited_nodes else "" for node in G.nodes()})
        for _, t in text.items():
            t.set_fontsize(9)
            t.set_verticalalignment("bottom")
        
        # Dark color for already visited nodes
        nx.draw_networkx_nodes(G, pos, nodelist=visited_nodes, node_color=dark_color, node_size=100)
        
        # Highlight the current node being traversed
        nx.draw_networkx_nodes(G, pos, nodelist=[node], node_color=highlight_color, node_size=100)

        # Highlight the edges in the current path
        #if i > 0:
        #    for j in range(i):
        #        nx.draw_networkx_edges(G, pos, edgelist=[(traversal_list[j], traversal_list[j+1])], edge_color="red", width=2)
        
        # Save the frame as a png file
        frame_path = f"frame_{i}.png"
        frames.append(frame_path)
        plt.savefig(frame_path)
        plt.clf()

def main():
    initialize(CIME_interface())
    plot_cgraph()
    animate_graph_traversal([cvars["COMP_OCN"], cvars["COMP_ATM"], cvars["COMP_LND"], cvars["COMP_ICE"], cvars['COMP_OCN_PHYS'], cvars['COMP_OCN_OPTION']])


if __name__ == "__main__":
    main()
