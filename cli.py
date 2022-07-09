#!/usr/bin/env python3

import logging
import os, sys
import cmd
import re
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

pth = os.path.dirname(os.path.dirname(os.path.dirname(os.path.join(os.path.abspath(__file__)))))
sys.path.append(pth)

logger = logging.getLogger("cmdCaseGen")

from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.config_var import ConfigVar, cvars
from visualCaseGen.config_var_str import ConfigVarStr
from visualCaseGen.init_configvars import init_configvars
from visualCaseGen.logic import logic

class cmdCaseGen(cmd.Cmd):

    intro = "\nWelcome to the cmdCaseGen command shell. Type help or ? to list commands."
    prompt = ">>> "
    file = None

    def __init__(self, exit_on_error=False):
        cmd.Cmd.__init__(self)
        self.ci = CIME_interface("nuopc")
        ConfigVar.reset()
        init_configvars(self.ci)
        logic.initialize(cvars, self.ci)
        self._init_configvar_options()
        self._exit_on_error = exit_on_error

    def printError(self, msg):
        if self._exit_on_error:
            sys.exit("ERROR: "+msg)
        else:
            logger.error(msg)

    def _init_configvar_options(self):
        for varname, var in cvars.items():
            if var.has_options_spec():
                var.refresh_options()

    def do_vars(self, arg):
        """
        vars: list assigned ConfigVars.
        vars -a: list all ConfigVars."""
        if arg in ['-a', 'a', '-all', 'all']:
            # list all variables
            for varname, var in cvars.items():
                print("{}={}".format(varname,var.value))
        else:
            # list set variables only
            for varname, var in cvars.items():
                if not var.is_none():
                    print("{}={}".format(varname,var.value))

    def completenames(self, text, *ignored):
        """ This gets called when a (partial or full) single word, i.e., param name,
        is to be completed. """
        complete_list = []
        for varname in cvars:
            if varname.startswith(text.strip()):
                complete_list.append(varname)
        return complete_list

    def completedefault(self, text, line, begidx, endidx):
        """ This completion method gets called when more than one words are already typed,
        i.e., when a parameter assignment is to be made."""
        if '=' in line:
            sline = line.split('=')
            varname = sline[0].strip()
            if ConfigVarStr.exists(varname):
                var = cvars[varname]
                assert var.has_options()
                options = var.options
                val_begin = sline[1].strip()
                if len(val_begin)>0:
                    return [opt for opt in options if opt.startswith(val_begin)]
                else:
                    return options
        return []


    def _assign_var(self, varname, val):
        try:
            var = cvars[varname]
            var.value = val
        except Exception as e:
            self.printError("{}".format(e))

    def default(self, line):
        """The default user input is variable assignment, i.e., key=value where key is a ConfigVarStr name
        and value is a valid value for the ConfigVarStr. If no value is provided, current value is printed."""

        # assign variable value
        if re.search(r'\b\w+\b *= *\b\w+\b', line):
            sline = line.split('=')
            varname = sline[0].strip()
            if ConfigVarStr.exists(varname):
                val = sline[1].strip()
                self._assign_var(varname, val)
            else:
                self.printError("Cannot find the variable {}. To list all variables, type: vars -a".format(varname))

        # query variable value
        elif re.search(r'^ *\b\w+ *$', line):
            varname = line.strip()
            if ConfigVarStr.exists(varname):
                val = cvars[varname].value
                print("{}".format(val))
            else:
                self.printError("{} is not a variable name or a command".format(varname))
        else:
            self.printError("Unknown syntax! Provide a key=value pair where key is a ConfigVarStr, e.g., COMP_OCN")

    ##def do_assertions(self, line):
    ##    """list all assertions"""
    ##    print(logic.universal_solver().assertions())

    def do_opts(self, line):
        """For a given varname, print all options and their validities"""
        varname = line.strip()
        if not re.search(r'^\b\w+\b$', varname):
            self.printError("Invalid syntax for the opts command. Provide a variable name.")
            return
        var = cvars[varname]
        if var.has_options():
            for opt in var._widget.options:
                print('\t', opt)
        else:
            self.printError("Variable {} doesn't have options".format(varname))
    
    def do_nullify(self, line):
        """Set a given variable to None"""
        varname = line.strip()
        if not re.search(r'^\b\w+\b$', varname):
            self.printError("Invalid syntax for the nullify command. Provide a variable name.")
            return
        var = cvars[varname]
        var.value = None

    def close(self):
        if self.file:
            self.file.close()
            self.file = None

    def do_exit(self, arg):
        """Close the command line interface."""
        print('Closing cmdCaseGen command shell')
        self.close()
        return True

    def do_x(self, arg):
        """Close the command line interface."""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Close the command line interface."""
        return self.do_exit(arg)

    def do_chg(self, arg):
        """Generate constraint hypergraph"""

        # plot parameters:
        width = 8
        height = 11
        dpi = 150
        node_size = 200
        node_font = 8
        angle = 30
        height_angle = 25
        view_dist = 9.0
        colors = ['skyblue', 'lightsalmon', 'yellowgreen', 'plum', 'orange', 'mediumseagreen', 'rosybrown', 'olivedrab']*3

        def get_node_shape(n):
            """Returns the node color and marker for a given graph node."""
            i = G.nodes[n]['li']
            color = colors[i]
            if G.nodes[n]['type'] == "V":
                marker = 'o'
            elif G.nodes[n]['type'] == "U":
                marker = 's'
            elif G.nodes[n]['type'] == "C":
                marker = 'D'
            elif G.nodes[n]['type'] == "O":
                marker = 'p'
            else:
                raise RuntimeError("Unknown node type")
            return color, marker

        def get_edge_shape(e):
            """Returns the edge linestyle, color, and alpha for a given graph node."""
            n0, n1 = e[0], e[1]
            i0 = G.nodes[n0]['li']
            i1 = G.nodes[n1]['li']
            if i0 == i1:
                return '-', colors[i0], 0.6
            else:
                return '--', colors[max([i0,i1])], 0.4


        fig, ax = plt.subplots(1, 1, figsize=(width, height), dpi=dpi, subplot_kw={'projection':'3d'})
        ax.set_box_aspect((1, 1, 2.0))

        G = logic.chg
        #pos = nx.spring_layout(G, k=4.0)#
        pos = nx.spring_layout(G, k=1.0)#
        xs = {n:pos[n][0] for n in pos}
        ys = {n:pos[n][1] for n in pos}

        # draw nodes:
        for ni, n in enumerate(G.nodes):
            color, marker = get_node_shape(n)
            x, y = xs[n], ys[n]
            z = - G.nodes[n]['li']
            ax.scatter(x, y, z, edgecolors='.2', s=node_size, c=color, marker=marker)
            ax.text(x, y, z, str(ni), color='.2', zorder=1000, fontsize=node_font, fontweight="bold", ha='center', va='center')

        # draw edges
        for e in G.edges:
            n0, n1 = e[0], e[1]
            x0, y0, z0 = pos[n0][0], pos[n0][1], - G.nodes[n0]['li']
            x1, y1, z1 = pos[n1][0], pos[n1][1], - G.nodes[n1]['li']
            linestyle, color, alpha = get_edge_shape(e)
            ax.plot([x0, x1], [y0,y1], [z0,z1], linestyle, c=color, alpha=alpha)

        # draw planes:
        xrange = max(xs.values()) - min(xs.values())
        yrange = max(ys.values()) - min(ys.values())
        ymin = min(ys.values()) - yrange*0.1
        ymax = max(ys.values()) + yrange*0.1
        xmin = min(xs.values()) - xrange*0.1 * (width/height)
        xmax = max(xs.values()) + xrange*0.1 * (width/height)
        xx, yy = np.meshgrid([xmin, xmax],[ymin, ymax])
        for i in range(len(logic.layers)):
            zz = np.zeros(xx.shape) - i
            # plane
            ax.plot_surface(xx, yy, zz, color=colors[i], alpha=0.15, zorder=i)

            # layer labels
            ax.text(0.2, 1.2, -i, "Layer {}".format(i),
                        color=colors[i], fontsize='large', fontweight='bold', zorder=1000, ha='left', va='center')

        ax.view_init(height_angle, angle)
        ax.dist = view_dist
        ax.set_axis_off()

        plt.tight_layout()
        plt.savefig("chg.png")

        # Finally, save label keys in a text file:
        with open("chg.txt", 'w') as chg_txt:
            for ni, n in enumerate(G.nodes):

                n_str = str(n)
                node_type = G.nodes[n]['type']
                if node_type == 'C':
                    n_str = 'If ({}, {})'.format(n[0], n[1])

                node_text = re.sub(' +|\n', ' ', n_str )
                chg_txt.write('{} {} {}\n'.\
                    format(ni, node_type, node_text )
                )

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.ERROR)
    cmdCaseGen().cmdloop()

