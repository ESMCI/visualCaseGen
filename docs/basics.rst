visualCaseGen Basics
====================

This section defines key concepts in visualCaseGen that will be referenced throughout the documentation.


Configuration Variable
-----------------------

Configuration variables are essential CESM settings that must be defined before creating a case.
These include choices like the model, model physics, resolution, and grid options that are set in
CESM XML and user namelist files. visualCaseGen provides an intuitive, form-based interface for
configuring these variables, ensuring compatibility and completeness. Only the variables required
for case instantiation are included in visualCaseGen; other settings that can be adjusted after
case creation, such as simulation duration, are not included in the GUI.

Stage
-----

In visualCaseGen, a stage represents a group of related CESM configuration variables that can be
set together. Examples of stages include models, physics options, and resolutions. Stages introduce
a logical hierarchy, where those listed earlier hold higher precedence. For instance, model selection
is a prerequisite for defining model physics, so the model stage takes precedence. visualCaseGen
guides users through each stage in the proper order, ensuring that configurations are compatible
at each step.

A stage is deemed complete when all of its configuration variables have been set. When a stage is
complete, visualCaseGen will automatically advance to the next stage. Users can also navigate
between stages by clicking the `Revert` button on the top bar of each Stage to return to the previous
stage or the `Proceed` button to advance to the next stage, but if there are any incomplete configuration
variables, visualCaseGen will prompt users to fill them in before proceeding. The `Defaults` button on 
the top bar of each stage allows users to quickly set all configuration variables to their default
values, if available. The `Info` button provides additional information about the stage and its 
configuration variables.

Standard vs Custom
------------------

During configuration, users can choose between standard and custom options for certain settings,
like compsets, resolutions, and model grids. Standard options are predefined CESM configurations
that are generally easier and safer to use, while custom options allow for greater flexibility.
visualCaseGen assists users through the custom configuration process to maximize compatibility,
but custom setups may require additional troubleshooting. For any issues with custom configurations,
please refer to the Troubleshooting section of this guide.

