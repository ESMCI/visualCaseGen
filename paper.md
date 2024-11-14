---
title: 'visualCaseGen: An Experiment Configuration Interface for Community Earth System Model'
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
 - name: NSF National Center for Atmospheric Research, Boulder CO
   index: 1
date: 13 August 2017
bibliography: paper.bib

---

# Summary

visualCaseGen is a graphical user interface (GUI) developed to streamline
the complex workflow of creating and configuring experiments with the 
Community Earth System Model (CESM), a leading climate model developed
by NSF’s National Center for Atmospheric Research (NCAR). visualCaseGen
guides users through key stages of experiment setup, ensuring that all
necessary high-level modeling decisions are compatible and consistent.

Built as a Jupyter-based GUI, visualCaseGen enables users to efficiently
browse standard CESM configurations or build new, custom ones. In standard
mode, users can explore and select from predefined (1) component sets, 
i.e., collections of model components, physics options, and other high-level model options, and 
(2) resolutions, i.e., combinations of grids corresponding to 
the discrete representations of each component’s spatial domains. In custom
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

