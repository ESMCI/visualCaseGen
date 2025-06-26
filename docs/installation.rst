Installation
======================================

visualCaseGen is presently bundled with a CESM distribution (fork) based on cesm3_0_beta06. The following
instructions guide you through obtaining and installing this specific CESM distribution with visualCaseGen.

Prerequisite
-------------

- A UNIX style operating system (Linux, macOS, etc.)
- Python
- Conda
- Git

.. warning::
  - If you are running visualCaseGen on a machine other than a standard CESM machine (e.g., derecho, casper),
    you will need to port CESM to your machine. For guidance on porting CESM, refer to the CESM documentation,
    or consult support through the CESM forum. If you 
    choose not to port CESM to your machine, you can still run visualCaseGen, but the final step of
    "case creation" will be disabled. Instead, you will have the option to print the necessary steps to manually
    create the configured case on a supported machine. If you are using a supported machine, you
    can run visualCaseGen as normal, and the final step of "case creation" will be enabled.


Download CESM with visualCaseGen
--------------------------------

To download the specific CESM distribution bundled with visualCaseGen, clone the CESM GitHub repository and
use the `git-fleximod` script that comes with CESM as a package manager, as follows. Note that downloading
CESM may take some time.

.. code-block:: bash

    git clone https://github.com/alperaltuntas/cesm.git -b cesm3_0_beta06_gui cesm3_0_beta06_gui
    cd cesm3_0_beta06_gui
    ./bin/git-fleximod update

This will download the required CESM version, including visualCaseGen.

Create the visualCaseGen conda environment
------------------------------------------

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

