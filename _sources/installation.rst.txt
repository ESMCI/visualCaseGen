Installation
======================================

visualCaseGen is presently bundled with a CESM distribution (fork) based on cesm3_0_beta03. The following
instructions guide you through obtaining and installing this specific CESM distribution with visualCaseGen.

Prerequisite
-------------

.. warning::
  The key prerequisite for installing visualCaseGen is that CESM cesm3_0_beta03 or a newer version is already
  ported on your machine. If this version (or later) is not yet ported, follow the CESM documentation
  instructions to port it first. Without this, visualCaseGen will not launch.

- Verify CESM port: Ensure CESM cesm3_0_beta03 or newer is ported on your machine. If not, follow the CESM
  documentation to port the required version.
- Conda Installation: Confirm that Conda is installed, either via Miniconda or Anaconda. You can install Miniconda
  from the following link:
  https://docs.conda.io/en/latest/miniconda.html

Download CESM with visualCaseGen
--------------------------------

To download the specific CESM distribution bundled with visualCaseGen, clone the CESM GitHub repository and
use the `git-fleximod` script that comes with CESM as a package manager, as follows. Note that downloading
CESM may take some time.

.. code-block:: bash

    git clone https://github.com/alperaltuntas/cesm.git -b cesm3_0_beta03_gui cesm3_0_beta03_gui
    cd cesm3_0_beta03_gui
    ./bin/git-fleximod update

This will download the required CESM version, including visualCaseGen.

Create the visualCaseGen conda environment
------------------------------------------

.. warning::
  If you are using a machine other than one of the supported systems (e.g., derecho, casper), you may need
  to modify the ccs_config/machines XML files in the newly downloaded CESM distribution. This may be required
  even if CESM cesm3_0_beta03 or a newer version is already ported on your machine. These modifications
  should match the adjustments made previously for the ported CESM version. For guidance on updating the
  ccs_config/machines XML files, refer to the CESM documentation, consult CESM support through the CESM forum,
  or submit an issue on the visualCaseGen GitHub repository. Users on supported machines can ignore this warning,
  as no changes are needed.

To create the `visualCaseGen` conda environment, navigate to the `visualCaseGen` directory and run the following
commands:

.. code-block:: bash

    cd visualCaseGen
    conda env create -f environment.yml

This will create the `visualCaseGen` conda environment. Activate the `visualCaseGen` conda environment by running
the following command:

.. code-block:: bash

    conda activate visualCaseGen

Verify Installation
------------------------------------------

To verify that visualCaseGen was installed correctly, run the test suite:

.. code-block:: bash

    pytest tests/

If the test suite completes successfully, visualCaseGen is ready for use. If any tests fail, please open an
issue on the visualCaseGen GitHub repository, including error messages and the installation steps you followed.

