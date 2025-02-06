---
title: 'visualCaseGen: An SMT-based Experiment Configurator for Community Earth System Model'
tags:
  - Python
  - cesm
  - climate modeling
  - constraint solver
  - SMT
authors:
  - name: Alper Altuntas
    orcid: 0000-0003-1708-9518
    affiliation: "1"
  - name: et al.
    orcid: 0000-0000-0000-0000
    affiliation: "1"
affiliations:
 - name: NSF National Center for Atmospheric Research, Boulder, CO
   index: 1
date: 13 August 2017
bibliography: paper.bib

---

# Introduction

visualCaseGen is a graphical user interface (GUI) designed to streamline the
creation and configuration of Community Earth System Model (CESM) experiments.
Developed at the NSF National Center for Atmospheric Research (NCAR), CESM is a
leading climate model capable of simulating the Earth's climate system at
varying levels of complexity [@danabasoglu2020community]. Configuring custom
CESM experiments demands a deep understanding of component compatibility, grid
configurations, parameterization schemes, and model hierarchies, making the
setup process highly complex and time-intensive, particularly for non-standard
and cutting-edge applications. visualCaseGen addresses these challenges by
providing an intuitive, interactive interface that automates and simplifies
experiment setup, significantly reducing configuration time and enhancing
usability for modelers.

To ensure consistency and compatibility, visualCaseGen incorporates a constraint
solver based on satisfiability modulo theories (SMT) [@de2011satisfiability].
This solver systematically analyzes dependencies between experiment settings,
detects conflicts, and provides detailed explanations of incompatibilities,
allowing users to make informed adjustments. the SMT-based approach enables
dynamic, real-time validation of model settings, significantly reducing setup
errors and ensuring that only scientifically viable configurations are selected.

On the frontend, visualCaseGen is implemented as a Jupyter-based GUI, offering
an intuitive, step-by-step interface for browsing standard CESM configurations,
defining custom experiment setups, and modifying grid and component settings.
Additionally, the tool features point-and-click utilities for creating and
modifying ocean bathymetry, along with custom land surface property tools,
further simplifying model customization.

By automating and simplifying CESM configuration, visualCaseGen makes the model
more accessible and custumizable, particularly for researchers exploring
hierarchical modeling [@maher2019model], idealized experiments
[@polvani2017less], or custom coupled simulations. As such, the tool allows
users to focus on their scientific objectives rather than technical setup
challenges, ultimately enabling a more efficient and streamlined experiment
workflow.


# Statement of need

CESM is a highly flexible and comprehensive
climate modeling system that allows researchers to simulate the interactions
between the atmosphere, ocean, land, ice, and river systems. While this
flexibility enables a wide range of scientific experiments, it also makes model
configuration highly complex and time-consuming. Setting up custom CESM
experiments requires navigating intricate component compatibility constraints,
grid configurations, and parameterization choices, often demanding extensive
expertise in the model’s internal structure. For non-standard experiments, users
must manually modify the CESM codebase and runtime paramter files, maintain
numerical and scientific consistency, and troubleshoot compatibility issues, a
process that is error-prone, tedious, and time-intensive.

visualCaseGen was developed to overcome these usability barriers and streamline
the CESM experiment setup process. As a GUI, visualCaseGen eliminates the need
for manual modifications and provides an intuitive, structured approach to
constructing new model configurations. It enables users to browse standard CESM
setups, create custom model configurations, and modify grids with ease,
significantly reducing setup complexity and time. By automating tedious
configuration tasks, visualCaseGen empowers researchers to focus on scientific
exploration rather than technical setup, streamlining model utilization for both
idealized and sophisticated climate modeling studies.

# Constraint Solver

One of the main challenges in configuring CESM experiments is ensuring that
different model settings remain compatible. CESM’s configuration involves
numerous interdependent components, grids, and parameterization choices, many of
which have strict compatibility constraints. visualCaseGen addresses this
challenge by integrating an SMT-based constraint solver, built using the Z3
solver [@de2008z3]. Z3 was chosen for its robust Python API, and its ability to
efficiently manage complex logical relationships and reason about compatibility
constraints, making it well-suited for handling CESM’s intricate configuration
dependencies.

In visualCaseGen, constraints are specified as key-value pairs, where the key
represents a Z3 logical expression defining a condition, and the value is the
error message displayed when the constraint is violated. The following examples
illustrate constraints of increasing complexity:

```python

LND_DOM_PFT >= 0.0:
    "PFT/CFT must be set to a nonnegative number",

Implies(OCN_GRID_EXTENT=="Regional", OCN_CYCLIC_X=="False"):
    "Regional ocean domain cannot be reentrant"
    "(due to an ESMF limitation.)",

Implies(And(COMP_OCN=="mom", COMP_LND=="slnd", COMP_ICE=="sice"),
        OCN_LENY<180.0):
    "If LND and ICE are stub, custom MOM6 grid must exclude poles"
    "to avoid singularities in open water",

```

These constraints enforce scientifically consistent model configurations, preventing
users from selecting incompatible options.

## Why Use a Constraint Solver?

Configuring CESM is inherently a constraint satisfaction problem (CSP), which
can quickly become computationally complex as the number of configuration
variables increases [@biere2009handbook]. Manually enforcing constraints would be impractical, making
an SMT solver an ideal choice. The benefits of using a solver include:

- **Detecting Hidden Conflicts:** Individual constraints may be satisfied
  independently, yet their combination can lead to conflicts that are nontrivial
  to detect manually.

- **Preventing Dead-Ends:** Without a solver, users may unknowingly select
  settings that lead to an unsatisfiable configuration, forcing them to restart
  their setup. Thanks to the solver, visualCaseGen dynamically guides users
  toward valid options.

- **Enabling Constraint Analysis:** The solver can answer critical questions, such as:
  - Are all constraints satisfiable?
  - Are there unreachable options that need adjustment?
  - Are any constraints redundant and can be optimized?

- **Scalability and Efficiency:** As the number of variables and constraints grows
  exponentially, manually checking compatibility becomes infeasible. The 
  solver efficiently handles large-scale constraint resolution, ensuring rapid
  feedback even for large number of configuration variables.

 
# The Stage Mechanism

A key backend concept in visualCaseGen is the Stage Mechanism, which structures
the CESM configuration process into consecutive steps (stages). Each stage
includes a set of related configuration variables that can be adjusted together.
Based on the user's selections, different stages are activated dynamically,
guiding the user through a structured workflow.

## Stage Pipeline

All possible stage paths collectively form the stage pipeline as shown in \autoref{fig:pipeline},
which dictates:

 - The sequence in which configuration variables are presented to the user. 
 - The precedence of variables: earlier stages have higher priority over later ones.

![The visualCaseGen stage pipeline, starting from the top node (1. Component Set) and ending at the bottom node (3. Launch). The user follows a path along this pipeline based on their modeling needs and selections. \label{fig:pipeline}](stage_pipeline.png)

A complexity arises when the same variable appears in multiple stages. This
is allowed as long as it is not reachable along the same path within the stage
pipeline. To prevent cyclic dependencies, the stage pipeline must therefore form a
directed acyclic graph (DAG), enabling a consistent variable precedence
hierarchy and eliminating the possibility of loops or contradictory variable
settings.

## Constraint Graph and its Traversal

Using the stage pipeline and specified constraints, visualCaseGen constructs a
constraint graph, as shown in \autoref{fig:cgraph}. In this graph:

 - Nodes represent configuration variables. 
 - Directed edges represent dependencies or constraints between variables.
 - Edges are directed from higher-precedence variables to lower-precedence variables.
 
![The visualCaseGen constraint graph. \label{fig:cgraph}](cgraph.png)

During the configuration process, when a user makes a selection, the constraint
graph is traversed to identify all variables that are affected by the selection.
This traversal is done in a breadth-first manner, starting from the selected
variable and following the edges in the direction of the constraints. The
traversal stops at variables whose options validities are not affected by the
selection. As such the traversal is limited to the variables that are directly
or indirectly affected by the user's selection, which in turn depends on the the
user input, stage hierarchy, and the specified constraints. By dynamically
re-evaluating constraints and adjusting available options, visualCaseGen
provides real-time feedback, preventing invalid configurations and ensuring
scientific consistency in CESM setups.

# Frontend 

The visualCaseGen frontend provides an intuitive and interactive interface for
configuring CESM experiments. Built with Jupyter ipywidgets [@ipywidgets], it
can operate on local
machines, HPC clusters, and cloud environments. This portability and flexibility allows
researchers to configure CESM experiments efficiently, whether prototyping
lightweight simulations on personal computers or running sophisticated applications on remote supercomputing
systems.

\autoref{fig:Stage1_7} displays an example stage from the visualCaseGen GUI,
where users can select the individual models to be coupled in their CESM
experiment. As the user makes selections, the GUI dynamically updates available
options by crossing out incompatible choices, ensuring that only valid
configurations are presented. This interactive feedback mechanism guides users
through the configuration process, helping them make informed decisions and
avoiding incompatible selections.

![The "Components" stage. \label{fig:Stage1_7}](Stage1_7.png)

At any stage, users can click on crossed-out options to view a
brief explanation of why a particular choice is incompatible with their current
selections, as illustrated in \autoref{fig:Stage1_8}. This feature helps guide
users through complex configuration dependencies, and helping them make informed
adjustments.

![Interactive feedback in incompatible choices. \label{fig:Stage1_7}](Stage1_8.png)

As another example of streamlining model customization, \autoref{fig:TopoEditor}
shows the TopoEditor widget that comes with visualCaseGen. This tool allows users
to interactively modify ocean bathymetry, enhancing customizability and
ease of use.

![TopoEditor widget \label{fig:TopoEditor}](TopoEditor.png)

# Remarks

In a recent study, @wu2021coupled configured an idealized CESM experiment to
study atmosphere-ocean interactions in simplified climate models
(\autoref{fig:wuEtAl}). Their approach involved modifying CESM to create two
idealized ocean-covered models, one without continents and another with a
pole-to-pole strip continent to investigate how simplified configurations affect
Hadley circulation, equatorial upwelling, and precipitation patterns. However,
setting up these experiments was a labor-intensive process that required
manually editing CESM, modifying runtime parameters, consulting experts for
component-specific adjustments, and extensive trial-and-error testing. As a
result, configuring the model took weeks before achieving a working setup.

![Sea surface temperature and precipitable water distribution from Aqua and Ridge planet simulations using CESM. Taken from [@wu2021coupled]. \label{fig:wuEtAl}](wuEtAl.png){height="300pt"}


visualCaseGen can significantly accelerate similar
studies by automating many aspects of experiment configuration. Instead of
manually modifying CESM files, modelers can use visualCaseGen’s interactive GUI
to define custom model setups, mix and match component configurations, and
automatically resolve compatibility constraints. The SMT-based constraint solver
ensures that only valid model settings are selected, reducing the need for
trial-and-error debugging. While complex custom cases may still require
fine-tuning, visualCaseGen allows modelers to generate an initial working
configuration in a matter of hours rather than weeks, greatly improving
efficiency and accessibility.

# Acknowledgements

This work was supported by the NSF Cyberinfrastructure for Sustained Scientific
Innovation (CSSI) program under award number 2004575. Special thanks to the
CESM Software Engineering Group for their support and feedback during the
development of visualCaseGen.

# References

