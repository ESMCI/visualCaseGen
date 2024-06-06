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


def gen_stage_pipeline(stage):
    """Generate a directed acyclic graph representing the stage pipeline.

    Parameters
    ----------
    stage : Stage
        The starting stage of the pipeline.

    Returns
    -------
    nx.DiGraph
        The directed graph representing the stage pipeline."""

    # Instantiate a directed graph object that will represent the stage pipeline
    G = nx.DiGraph()

    # Traverse the entire stage tree using depth-first search
    while (next := stage.get_next(full_dfs=True)) is not None:
        if stage.children_have_conditions():
            for child in stage._children:
                G.add_edge(stage, child)
                G.add_edge(child, child._children[0])
        else:
            # The actual next stage that would be visited during runtime
            runtime_next = stage.get_next(full_dfs=False)
            if runtime_next:
                G.add_edge(stage, runtime_next)
        stage = next

    assert nx.is_directed_acyclic_graph(
        G
    ), "The stage tree is not a directed acyclic graph."
    return G


def plot_stage_pipeline(G, output_file=None):
    """Plot the stage pipeline."""
    plt.figure(figsize=(6, 12))
    # pos = graphviz_layout(G, prog="sfdp")
    pos = graphviz_layout(G, prog="dot")
    nx.draw(
        G,
        pos,
        with_labels=False,
        edge_color="gray",
        node_color="powderblue",
        font_size=6,
    )
    text = nx.draw_networkx_labels(G, pos)
    for _, t in text.items():
        t.set_rotation(-15)
        t.set_verticalalignment("center")

    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()


def generate_path_animation(G, start, end, output_file):
    """Generate an animation of the possible paths from start to end in the stage pipeline.
    This will generate a single png image for each path from start to end, highlighting the edges
    in the path in red. These png files can be combined into a gif by running:
        $ convert -delay 100 -loop 0 stage_pipeline_*.png stage_pipeline.gif

    Parameters
    ----------
    G : nx.DiGraph
        The directed graph representing the stage pipeline.
    start : Stage
        The starting stage.
    end : Stage
        The ending stage.
    """
    # Find all possible paths from start to end
    all_paths = nx.all_simple_paths(G, start, end)

    # Iterate over each path
    for p, path in enumerate(all_paths):
        # Create a copy of the graph to highlight the current path
        highlighted_G = G.copy()

        for edge in highlighted_G.edges():
            highlighted_G[edge[0]][edge[1]]["color"] = "gray"
            highlighted_G[edge[0]][edge[1]]["penwidth"] = 1.0

        # Highlight the edges in the current path
        for i in range(len(path) - 1):
            highlighted_G[path[i]][path[i + 1]]["color"] = "red"
            highlighted_G[path[i]][path[i + 1]]["penwidth"] = 2.0

        colors = [highlighted_G[u][v]["color"] for u, v in highlighted_G.edges()]
        weights = [highlighted_G[u][v]["penwidth"] for u, v in highlighted_G.edges()]

        # Generate the plot for the current path
        plt.figure(figsize=(6, 12))
        pos = graphviz_layout(highlighted_G, prog="dot")
        nx.draw(
            highlighted_G,
            pos,
            edge_color=colors,
            with_labels=False,
            node_color="powderblue",
            font_size=6,
            width=weights,
        )
        text = nx.draw_networkx_labels(highlighted_G, pos)
        for _, t in text.items():
            t.set_rotation(-15)
            t.set_verticalalignment("center")

        # Save the plot as an image
        image_file = f"{output_file}_{p}.png"
        print(f"Saving image to {image_file}")
        plt.savefig(image_file)
        plt.close()


def main():
    initialize(CIME_interface())
    G = gen_stage_pipeline(Stage.first())
    plot_stage_pipeline(G)
    # generate_path_animation(G, Stage.first(), Stage._top_level[-1], "stage_pipeline")


if __name__ == "__main__":
    main()
