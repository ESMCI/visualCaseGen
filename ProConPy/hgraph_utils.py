import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
from ProConPy.config_var import ConfigVar
from z3 import BoolRef

def hgraph_to_nxgraph(hgraph):
    """Convert a given hypergraph to a networkx graph."""

    nxgraph = nx.DiGraph()

    # Add nodes
    for node in hgraph:
        nxgraph.add_node(node)
    
    # Add edges
    for node, vars2constraints in hgraph.items():
        for neighbor in vars2constraints:
            nxgraph.add_edge(node, neighbor)
    
    return nxgraph

def plot_nxgraph(hgraph):

    """Plot the hypergraph using networkx and matplotlib."""
    
    nxgraph = hgraph_to_nxgraph(hgraph)

    def get_node_style(n):
        #if isinstance(nxgraph.nodes[n], ConfigVar):
        if isinstance(n, ConfigVar):
            return "o", "moccasin"
        elif isinstance(n, BoolRef):
            return "s", "lightblue"
        else:
            raise ValueError(f"Unknown node type: {n}")
    
    def get_edge_style(e):
        n0, n1 = e[0], e[1]
        arrowprops = {'arrowstyle': '->', 'color': 'gray', 'alpha': 0.3, 'linewidth': 1.5, 'shrinkA': 12, 'shrinkB': 12}
        return arrowprops
    
    width = 6
    height = 3
    dpi = 150
    node_size = 200
    node_font = 8
    
    fig, ax = plt.subplots(1, 1, figsize=(width, height), dpi=dpi)

    # determine node positions:
    dx = 1.0
    dy = 1.0
    xs, ys = {}, {}
    for ni, n in enumerate(nxgraph.nodes):
        xs[n] = dx * ni
        if isinstance(n, ConfigVar):
            ys[n] = 0
        elif isinstance(n, BoolRef):
            ys[n] = - dy
        else:
            raise ValueError(f"Unknown node type: {n}")
    
    # draw nodes
    for ni, n in enumerate(nxgraph.nodes):
        marker, color = get_node_style(n)
        ax.scatter(xs[n], ys[n], s=node_size, c=color, marker=marker, edgecolor="black", linewidth=1.5)
        ax.text(xs[n], ys[n], str(ni), color="black", fontsize=node_font, ha="center", va="center")
    
    # draw edges
    for e in nxgraph.edges:
        n0, n1 = e[0], e[1]
        x0, y0 = xs[n0], ys[n0]
        x1, y1 = xs[n1], ys[n1]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=get_edge_style(e))

    # before showing the plot, write node labels to a file:
    with open("chg.txt", "w") as f:
        for ni, n in enumerate(nxgraph.nodes):
            f.write(f"{ni}: {n}\n")

    plt.tight_layout()
    ax.set_axis_off()
    plt.show()
