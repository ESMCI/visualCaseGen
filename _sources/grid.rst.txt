Stage 2/3: Grid
===============

The second major step in configuring your CESM case is choosing a resolution, which
is a specific set of grids for each active and data model in the compset. You may 
select either a standard, out-of-the-box resolution or create a custom one by combining
existing model grids. In `Custom` mode, you can also generate custom model grids for CLM and/or MOM6
using auxiliary tools included in visualCaseGen. Begin by selecting between `Standard`
and `Custom` grid modes.

.. image:: assets/Stage2_1.png

.. note:: In CESM terminology, *resolution* and *grid* are often used interchangeably,
   both referring to the combination of model grids used in a CESM simulation. Unless 
   specifically noted as a *model grid* (i.e., a grid unique to a particular component,
   such as the ocean grid), the term *grid* in this context should be understood as
   *resolution*, meaning the full collection of *model grids* used in a particular CESM case.

Standard Grids
------------------

Select from the available list of resolutions (combinations of model grids) below.
Resolutions known to be incompatible with your chosen compset have been omitted 
from this list. Use the search box to refine the list further. For exact matches,
use double quotes; otherwise, the search will display all grids containing one 
or more of the search terms.

.. image:: assets/Stage2_2.png

After selecting a grid, visualCaseGen will advance to the `Launch` stage, where
you can create your CESM case using the chosen compset and grid configuration.

Custom Grids
------------------

In Custom Grid mode, you can build a custom grid by mixing and matching standard 
model grids or generating new MOM6 and/or CLM grids with specialized tools that come with visualCaseGen.
Start by specifying a path to save the new grid files and a name to refer to this
new grid in the configuration process and beyond.

.. image:: assets/Stage2_3.png

After clicking `Select`, a file browser will open to help you locate your preferred
directory for saving the new grid files. Once the directory is selected, enter the
new grid name in the text box at the top right and click `Select` to proceed.

.. image:: assets/Stage2_4.png

Atmosphere Grid
~~~~~~~~~~~~~~~

Next, choose an atmosphere grid from the list of compatible options based on the
compset you selected in the `Compset` stage. Use the search box to filter options if needed.
This chosen atmosphere grid will be integrated with other model grids to form your custom CESM grid (resolution).

.. image:: assets/Stage2_5.png

Ocean Grid
~~~~~~~~~~

For the ocean grid, if MOM6 is selected as the ocean model, you can either select a standard
ocean grid or create a new MOM6 grid. When creating a new MOM6 grid, you'll specify parameters
such as grid extent and resolution, after which you'll be directed to a separate notebook that
uses the `mom6_bathy` tool to generate the new grid and bathymetry.

If using a standard ocean grid, select one from the list compatible with your chosen compset
and atmosphere grid. If creating a new MOM6 grid, complete the required parameters, then proceed
to launch the `mom6_bathy` tool for final customization.

.. image:: assets/Stage2_6.png

After specifying all ocean grid parameters, click `Launch mom6_bathy`. This will open an 
auto-generated Jupyter notebook where you can fine-tune the ocean grid bathymetry and generate
all necessary input files. For more details on mom6_bathy, refer to its documentation: https://ncar.github.io/mom6_bathy/

.. note:: If the `mom6_bathy` notebook doesn't open automatically, make sure that your browser allows
  pop-ups from visualCaseGen. If the notebook still doesn't open, you can manually launch it by
  navigating to the `mom6_bathy_notebooks/` directory in your visualCaseGen installation and opening
  the notebook corresponding to your custom grid.


Land Grid
~~~~~~~~~

Following ocean grid selection or creation, you'll move to land grid selection. If CLM is chosen
as the land model, you can also modify an existing CLM grid. If so, select a base land grid for
customization.

.. image:: assets/Stage2_7.png

.. note:: **Initialization of Custom Land Points:**
  When users define their own continental geometries, the model initializes land points
  by reading an initial conditions file (`finidat` specified in the CLM namelist). The model 
  interpolates the nearest neighbor information to populate land points that lack existing data.

.. note:: **Runoff Behavior with Idealized Land:**
    In scenarios with idealized land configurations, the new land points do not have an 
    updated routing map to direct water downstream. As a result, runoff from these land points
    is routed to the nearest ocean point. To verify that water is not lost in the process, users
    can consult the budget tables available in the log files.
    These tables provide detailed information on water budgets and confirm the conservation of water within the model.


.. note:: Detailed instructions on customizing an existing CLM grid will be added here shortly.

Once atmosphere, ocean, and land grids have been chosen or created, custom grid setup is complete.
visualCaseGen will guide you to the final stage, `Launch`, where you can create a CESM case based on
the specified compset and grid.