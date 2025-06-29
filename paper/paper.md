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
  - name: Manish Venumuddula
    orcid: 0009-0009-5047-2018
    affiliation: "1"
  - name: Isla R. Simpson
    orcid: 0000-0002-2915-1377
    affiliation: "1"
  - name: Scott D. Bachman
    orcid: 0000-0002-6479-4300
    affiliation: "1"
  - name:  Samuel Levis
    orcid: 0000-0003-4684-6995
    affiliation: "1"
  - name:  Brian Dobbins
    orcid: 0000-0002-3156-0460
    affiliation: "1"
  - name: William J. Sacks
    orcid: 0000-0003-2902-5263
    affiliation: "1"
  - name: Gokhan Danabasoglu
    orcid: 0000-0003-4676-2732
    affiliation: "1"

affiliations:
 - name: U.S. National Science Foundation National Center for Atmospheric Research (NSF NCAR), Boulder, CO
   index: 1
date: 13 August 2017
bibliography: paper.bib

---

# Introduction

visualCaseGen is a graphical user interface (GUI) designed to streamline the
creation and configuration of Community Earth System Model (CESM) experiments.
CESM is a highly flexible, state-of-the-art climate model that allows researchers
to simulate the Earth system across a wide range of spatial and temporal scales
and at varying levels of complexity, depending on scientific objectives [@danabasoglu2020community].
However, configuring non-standard or idealized CESM experiments is often a technically
demanding and time-consuming process, requiring detailed knowledge of component
compatibility, grid definitions, parameterization schemes, and model hierarchies.
visualCaseGen simplifies this process by guiding users through each stage of
experiment setup and automating key configuration steps via an intuitive, 
interactive interface.

To ensure consistency and compatibility across various model settings, visualCaseGen
incorporates a constraint solver based on satisfiability modulo theories (SMT)
[@de2011satisfiability]. This solver systematically analyzes dependencies between
configuration parameters, detects conflicts, and provides detailed explanations of
incompatibilities, allowing users to make informed adjustments. The SMT-based
approach enables dynamic, real-time validation of model settings, significantly
reducing setup errors and ensuring that only scientifically viable configurations
are selected.

On the frontend, visualCaseGen is implemented as a Jupyter-based GUI, offering
an intuitive, step-by-step interface for browsing standard CESM configurations,
defining custom experiment setups, and modifying grid and component settings.
Designed with a wizard-like interface, visualCaseGen walks users through each
stage of the CESM configuration process, ensuring that all necessary settings
are selected in a logical sequence while dynamically updating available options
based on user choices. Additionally, the tool features utilities for creating
and editing model input files, such as ocean grid, bathymetry, and land
surface properties, further simplifying model customization and
minimizing the need for manual file creation and modification.

By automating and simplifying CESM configuration, visualCaseGen makes the model
more accessible and custumizable, particularly for researchers exploring
hierarchical modeling [@maher2019model], idealized experiments
[@polvani2017less], or custom coupled simulations. As such, the tool allows
users to focus on their scientific objectives rather than technical setup
challenges, ultimately enabling a more efficient and streamlined experiment
workflow.


# Statement of need

CESM is a highly flexible and comprehensive modeling framework that
encompasses multiple components representing the atmosphere, ocean, land,
ice, river, biogeochemistry, and other systems. While this
flexibility supports a wide range of scientific experiments, it also introduces
significant complexity in model configuration. Setting up custom CESM
experiments requires navigating intricate component compatibility constraints,
grid configurations, and parameterization choices, often demanding extensive
expertise in the model’s internal structure. For non-standard experiments, users
must manually modify CESM’s codebase and runtime parameter files, maintain
numerical and scientific consistency, and troubleshoot compatibility issues.
This process is time-intensive, error-prone, and can take weeks before yielding
a functional setup.

A recent study by @wu2021coupled exemplifies these challenges. Their work
involved configuring an idealized CESM experiment to study atmosphere-ocean
interactions using two simplified aquaplanet models: one without continents and
another with a pole-to-pole strip continent. The goal was to investigate how
these configurations influence Hadley circulation, equatorial upwelling, and
precipitation patterns (\autoref{fig:wuEtAl}). However, setting up these
experiments required extensive manual intervention, including modifying CESM
codebase, creating custom input files, adjusting runtime parameters, consulting
domain experts for component-specific configurations, and conducting numerous
trial-and-error iterations. visualCaseGen was developed to address such
usability barriers and streamline CESM experiment setup. As a graphical user
interface (GUI), it eliminates the need for manual modifications and provides an
intuitive, structured workflow for constructing model configurations. 

![Sea surface temperature and precipitable water distribution from Aqua and
Ridge planet simulations using CESM. Adapted from @wu2021coupled.
\label{fig:wuEtAl}](wuEtAl.png){height="280pt"}

# Constraint Solver

One of the main challenges in configuring CESM experiments is ensuring that
different model settings remain compatible. CESM’s configuration involves
determining components, physics, grids, and parameterization choices, many of
which have strict compatibility constraints. visualCaseGen addresses this
challenge by integrating an SMT-based constraint solver, built using the Z3
solver [@de2008z3]. Z3 was chosen for its robust Python API and its efficiency
in managing complex logical relationships involving multiple parameter types
such as integers, reals, booleans, and strings. As such, Z3 is well suited 
to handling the intricate dependencies and constraints inherent in CESM
configurations.

In visualCaseGen, constraints are specified as key-value pairs, where the key
represents a Z3 logical expression defining a condition, and the value is the
error message displayed when the constraint is violated. These constraints
enforce compatibility rules and prevent invalid model configurations. Below
are three examples of visualCaseGen constraints with increasing complexity,
demonstrating how the SMT solver can enforce simple value bounds, conditional
dependencies, and more complex multi-component logical rules:

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
  feedback even for large number of variables.

 
# The Stage Mechanism

A key backend concept in visualCaseGen is the Stage Mechanism, which structures
the CESM configuration process into consecutive steps (stages). Each stage
includes a set of related configuration variables that can be adjusted together.
Based on the user's selections, different stages are activated dynamically,
guiding the user through a structured workflow.

## Stage Pipeline

All possible stage paths collectively form the stage pipeline as shown in
\autoref{fig:pipeline}, which dictates the sequence in which configuration
variables are presented to the user, and the *precedence of variables* where
earlier stages have higher priority over later ones. A complexity arises when
the same variable appears in multiple stages. This is allowed as long as it is
not reachable along the same path within the stage pipeline. To prevent cyclic
dependencies, the stage pipeline must therefore form a directed acyclic graph
(DAG), enabling a consistent variable precedence hierarchy and eliminating the
possibility of loops or contradictory variable settings.

![The visualCaseGen stage pipeline, starting from the top node (1. Component Set) and ending at the bottom node (3. Launch). The user follows a path along this pipeline based on their modeling needs and selections. \label{fig:pipeline}](stage_pipeline.png)

## Constraint Graph and its Traversal

Using the stage pipeline and specified constraints, visualCaseGen constructs a
constraint graph, as shown in \autoref{fig:cgraph}. In this graph:

 - Nodes represent configuration variables. 
 - Directed edges represent dependencies or constraints between variables.
 - Edges are directed from higher-precedence variables to lower-precedence variables.
 
During the configuration process, when a user makes a selection, the constraint
graph is traversed to identify all variables that are affected by the selection.
This traversal is done in a breadth-first manner, starting from the selected
variable and following the edges in the direction of the constraints. The
traversal stops at variables whose options' validities are not affected by the
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

![The visualCaseGen constraint graph. \label{fig:cgraph}](cgraph.png)

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

![Interactive feedback in incompatible choices. \label{fig:Stage1_8}](Stage1_8.png)

As another example of streamlining model customization, \autoref{fig:TopoEditor}
shows the TopoEditor widget that comes with visualCaseGen. This tool allows users
to interactively modify ocean bathymetry, enhancing customizability and
ease of use.

![TopoEditor widget \label{fig:TopoEditor}](TopoEditor.png)

# Remarks

visualCaseGen can significantly accelerate CESM experiment setup for a wide
range of studies by automating many aspects of experiment configuration. Instead
of manual intervention, modelers can use visualCaseGen’s interactive
GUI to define model setups, mix and match component configurations,
generate custom grids and parameters. The SMT-based constraint solver
ensures that only valid model settings are selected, reducing the need for
trial-and-error debugging. While complex custom cases may still require
fine-tuning, visualCaseGen allows modelers to generate an initial working
configuration in a matter of hours rather than weeks, greatly improving
efficiency and ease-of-use.

By automating tedious configuration tasks, visualCaseGen enables researchers to
focus on scientific exploration rather than technical setup, making CESM more
accessible for both idealized and complex climate modeling studies.

# Acknowledgements

This work was supported by the NSF Cyberinfrastructure for Sustained Scientific
Innovation (CSSI) program under award number 2004575. Special thanks to the
CESM Software Engineering Working Group for their support and feedback during
the development of visualCaseGen.

The NSF National Center for Atmospheric Research (NCAR) is a major facility
sponsored by the NSF under Cooperative Agreement No. 1852977.

# References

