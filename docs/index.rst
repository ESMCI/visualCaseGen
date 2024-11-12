.. visualCaseGen documentation master file, created by
   sphinx-quickstart on Sun Oct 27 13:59:27 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to visualCaseGen!
=========================================

visualCaseGen is a Jupyter-based graphical user interface (GUI) designed to streamline
the creation and configuration of Community Earth System Model v.3 (CESM3) cases.
The visualCaseGen GUI allows users to:

- **Browse Standard CESM Configurations:** Easily explore and select from available CESM compsets
  and resolutions.
- **Create Custom Configurations**: Rapidly customize CESM experiments with advanced options for component
  selection, grid generation, and configuration.

Key Features
------------

- **Easy Case Setup:** Intuitive interface for configuring experiments.
- **Hierarchical Modeling:** Combine different complexity levels across components.
- **Flexible Configurations:** Mix and match models and grids with compatibility guidance.
- **Automated Case Creation:** Generates input files and handles XML/namelist adjustments.
- **Modify CLM Inputs:** Easily adjust land masks and surface datasets with a form-based interface.
- **MOM6 Grid & Bathymetry Customization:** Create or modify grids and bathymetries with a point-and-click tool.

.. image:: assets/demo3.gif

Typical Workflow
----------------

- **Launch:** Open the visualCaseGen GUI within your Jupyter notebook environment.
- **Select Compset:** Choose from available standard CESM compsets or create a custom one by selecting
  models, physics options, and other settings for each component (e.g., atmosphere, ocean, land, ice).
- **Define Resolution:** Select a compatible standard resolution or create a custom one by combining
  different grids for each model component or generating new ones.
- **Generate Case:** Once your compset and resolution are set, visualCaseGen will create the CESM case,
  automatically generating required input files and making all necessary modifications to CESM XML and
  user namelist files.

For more information on each step, please refer to the corresponding sections in this user guide.

.. toctree::
   :maxdepth: 3
   :caption: User Manual:

   installation
   open
   basics
   creating_case
   compset
   grid
   launch
   troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: Examples:

   ridge
   fillindian