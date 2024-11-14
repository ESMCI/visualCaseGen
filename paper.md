---
title: 'visualCaseGen: An Interactive Experiment Configurator for Community Earth System Model'
tags:
  - Python
  - cesm
  - climate modeling
  - galactic dynamics
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

visualCaseGen is a graphical user interface (GUI) developed to streamline
the complex workflow of creating and configuring experiments with the 
Community Earth System Model (CESM), a leading climate model developed
by NSF National Center for Atmospheric Research (NCAR). visualCaseGen
guides users through key stages of experiment setup, ensuring that all
necessary high-level modeling decisions are compatible and consistent.

Built as a Jupyter-based GUI, visualCaseGen enables users to efficiently
browse standard CESM configurations or build new, custom ones. In standard
mode, users can explore and select from predefined (1) *component sets*, 
i.e., collection of models to be coupled, along with physics packages and
other high-level option for each individual model, and 
(2) *resolutions*, i.e., combinations of grids representing each component’s
spatial domains. In custom
configuration mode, users can further extend CESM’s capabilities by creating
unique component sets and resolutions, mixing complexity levels across 
components and generating idealized or sophisticated configurations suited to 
specific research goals. 

With either configuration mode, visualCaseGen 
enhances the setup process by flagging incompatible options and providing
detailed descriptions of constraints, guiding users to make informed and
valid choices in their experiment designs. This framework makes CESM 
experiment configuration more accessible, significantly reducing setup time
and expanding the range of modeling applications available to users.


# Statement of need

Earth system models (ESMs), such as CESM, are composed of individual models that
simulate different components of the climate system, such as the atmosphere, ocean,
land, sea ice, glaciers, and rivers. These models are coupled together to represent
the interactions between these components, enabling a comprehensive simulation of
the Earth's climate system.

The increasing pressure to accurately project the future of our climate system has
driven the development of highly complex ESMs that simulate a wide range of processes [cite].
While this complexity is crucial for producing accurate climate projections,
it also brings significant challenges. The high computational demands make running
simulations increasingly resource-intensive, and the complexity makes it difficult 
to design focused experiments that isolate specific processes or behaviors.

To manage the increasing complexity and computational demands of modern ESMs,
a framework is needed to simplify coupled ESMs in a consistent and coherent manner,
offering model components with varying levels of complexity or allowing full-physics
components to be used in an idealized context. For example, a “dry” atmospheric
core can replace complex physics with simple Newtonian relaxation of the temperature
field [cite], or a full-physics atmosphere can be coupled with idealized continental
geometry.

Given the configuration complexity of ESMs like CESM, especially for custom or novel
applications, a user-friendly framework is essential for navigating the model hierarchy
and adjusting both model complexity and domain geometry. Such a framework can therefore
empower modelers to balance simplified and detailed representations across model
components, making it easier to isolate processes and conduct experiments for both
fundamental and applied climate studies.

# What visualCaseGen Does  

...

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

