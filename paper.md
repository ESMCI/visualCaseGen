---
title: 'visualCaseGen: An Experiment Configurator for Community Earth System Model'
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

# Summary

visualCaseGen is a graphical user interface (GUI) designed to streamline the
creation and configuration of Community Earth System Model (CESM) experiments.
Developed at the NSF National Center for Atmospheric Research (NCAR), CESM is a
leading climate model capable of simulating the Earth's climate system at
varying levels of complexity. However, configuring custom CESM experiments
requires intricate knowledge of component compatibility, grid settings,
parameterization choices, and model hierarchies, making the setup process
complex and time-consuming for unique or breakthrough applications.
visualCaseGen provides a user-friendly interface that simplifies these tasks,
significantly reducing setup time and improving ease of use for modelers.

To ensure consistency and compatibility, visualCaseGen incorporates a constraint
solver based on satisfiability modulo theories (SMT). This solver systematically
analyzes dependencies between experiment settings, detects conflicts, and
provides detailed explanations of incompatibilities, allowing users to make
informed adjustments.

On the frontend, visualCaseGen is implemented as a Jupyter-based GUI, offering
an intuitive, step-by-step interface for browsing standard CESM configurations,
defining custom experiment setups, and modifying grid and component settings.
Additionally, the tool features point-and-click utilities for creating and
modifying ocean bathymetry, along with custom land surface property tools,
further simplifying model customization.

By automating and simplifying CESM configuration, visualCaseGen makes the model
more accessible and custumizable, particularly for researchers exploring
hierarchical modeling, idealized experiments, and custom coupled simulations.
This tool allows users to focus on their scientific objectives rather than
technical setup challenges, ultimately enabling a more efficient and streamlined
experiment workflow.


# Statement of need

The Community Earth System Model (CESM) is a highly flexible and comprehensive
climate modeling system that allows researchers to simulate the interactions
between the atmosphere, ocean, land, ice, and river systems. While this
flexibility enables a wide range of scientific experiments, it also makes model
configuration highly complex and time-consuming. Setting up CESM experiments
requires navigating intricate component compatibility constraints, grid
configurations, and parameterization choices, often demanding extensive
expertise in the model’s internal structure. In  particular, for non-standard
experiments, users must manually modify XML an namelist files, maintain
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

One of the key challenges in configuring CESM is ensuring that different
component settings are compatible. visualCaseGen addresses this challenge by
incorporating an SMT-based constraint solver built using the Z3 SMT solver
[@de2008z3]. Z3 was chosen for its ability to manage complex logical
relationships and efficiently reasoning about (in)compatibilities.

In visualCaseGen, constraints are specified as key-value pairs, where the key
represents a Z3 logical expression defining a condition, and the value is the
error message displayed when the constraint is violated. The following examples
illustrate constraints of increasing complexity:

```python

LND_DOM_PFT >= 0.0:
    "PFT/CFT must be set to a nonnegative number",

Implies(OCN_GRID_EXTENT=="Regional", OCN_CYCLIC_X=="False"):
    "Regional ocean domain cannot be reentrant (due to an ESMF limitation.)",

Implies(And(COMP_OCN=="mom", COMP_LND=="slnd", COMP_ICE=="sice"), OCN_LENY<180.0):
    "If LND and ICE are stub, custom MOM6 grid must exclude poles (singularity).",

```

These constraints enforce scientifically valid model configurations, preventing
users from selecting incompatible options.


## Why Use a Constraint Solver?

Configuring CESM is inherently a constraint satisfaction problem (CSP), which
can quickly become computationally complex as the number of configuration
variables increases. Manually enforcing constraints would be impractical, making
an SMT solver an ideal choice for efficiently managing interdependencies.

The benefits of using a solver like Z3 in visualCaseGen include:

- *Detecting Hidden Conflicts:* Individual constraints may be satisfied
  independently, yet their combination can lead to conflicts that are nontrivial
  to detect manually.

- *Preventing Dead-Ends:* Without a solver, users may unknowingly select
  settings that lead to an unsatisfiable configuration, forcing them to restart
  their setup. Thanks to the solver, visualCaseGen dynamically guides users
  toward valid options.

- *Enabling Constraint Analysis:* The solver can answer critical questions, such as:
  - Are all constraints satisfiable?
  - Are there unreachable options that need adjustment?
  - Are any constraints redundant and can be optimized?

- Scalability and Efficiency: As the number of variables and constraints grows
  exponentially, manually checking compatibility becomes infeasible. The visualCaseGen
  constraint solver efficiently handles large-scale constraint resolution, ensuring rapid
  feedback  even for large number of CESM configuration variables.










## The stage mechanism 


# Frontend 



# Workflow 

With either configuration mode, visualCaseGen 
enhances the setup process by flagging incompatible options and providing
detailed descriptions of constraints, guiding users to make informed and
valid choices in their experiment designs. This framework makes CESM 
experiment configuration more accessible, significantly reducing setup time
and expanding the range of modeling applications available to users.


# Remarks



In standard
mode, users can explore and select from predefined (1) *component sets*, 
i.e., collection of models to be coupled, along with physics packages and
other high-level option for each individual model, and 
(2) *resolutions*, i.e., combinations of grids representing each component’s
spatial domains. In custom
configuration mode, users can further extend CESM’s capabilities by creating
unique component sets and resolutions, mixing complexity levels across 
components and generating idealized or sophisticated configurations suited to 
specific research goals. 

# The visualCaseGen package

The visualCaseGen project is designed to address the challenges of 
configuring and running idealized or complex simulations with CESM. As a graphical 
user interface (GUI), visualCaseGen simplifies the process of model 
configuration by providing an intuitive platform for users to interact 
with CESM's model hierarchy. Users can seamlessly browse predefined 
configurations or create custom setups, adjusting individual 
components such as the atmosphere, ocean, and land models, as 
well as associated physics packages and grid resolutions. By 
guiding users through the setup process, visualCaseGen ensures 
that all components are compatible and consistent.

This package empowers both novice and expert users to configure CESM 
in a way that aligns with their specific research needs. With a focus 
on accessibility, visualCaseGen reduces the time and expertise required 
to properly configure CESM, making high-level climate simulations more 
approachable and easier to execute. This flexibility helps to extend 
the model’s application range, allowing users to experiment with both 
simple and complex configurations depending on the scientific objectives 
at hand.

A typical workflow of visualCaseGen, consisting of (1) component set
configuration, (2) grid selection or construction, and, finally (3)
launching of the experiemnt, is captured in the screenshot of the GUI
(Figure ...)


# How visualCaseGen Works

...


# Software Design

lorem ipsun

## The stage mechanism

lorem ipsum

## Constraint specification and solver

lorem ipsum, SMT-based, z3py, constraint graph, ...

## visual elements and dynamic behavior

ipywidgets, traitlets, ...

highly portable, robust, familiar to scientists, ...

# Figures

Figures can be included like this:
![Caption for example figure.\label{fig:example}](figure.png)
and referenced from text using \autoref{fig:example}.

Figure sizes can be customized by adding an optional second parameter:
![Caption for example figure.](figure.png){ width=20% }

# Acknowledgements

We acknowledge ...

# References

