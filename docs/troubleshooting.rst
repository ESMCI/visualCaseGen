Troubleshooting
======================================

Below are some common issues that users may encounter while using visualCaseGen and their solutions.
If the suggested solutions do not resolve the issue, or if you encounter a different problem, please
open an issue on the visualCaseGen GitHub repository: https://github.com/ESMCI/visualCaseGen/issues/new

Commonly Encountered Issues
---------------------------

- **Error displaying widget: model not found:**
  This message generally appears when a previously run 
  `GUI.ipynb` notebook is re-opened. This error message doesn't generally indicate a problem with the GUI,
  and should dissapear after running the cell with the `from visualCaseGen import gui; gui` code.

- **ModuleNotFoundError:** No module named `z3`, `ipyfilechooser`, etc.: This error indicates that either
  the `visualCaseGen`` conda environment is not installed correctly, it was not chosen as the active environment,
  or it was not chosen as the kernel in the Jupyter notebook. To resolve this issue, ensure that the `visualCaseGen`
  conda environment is installed correctly and activated. If the issue persists, try restarting the Jupyter notebook
  kernel and selecting the `visualCaseGen` environment as the kernel.

- **Hanging Loadbar:** If the loadbar hangs after clicking the `Start` button, click the `Help` button on the top
  right corner of the welcome dialog to see if any error messages are displayed. If so, submit an issue on the
  visualCaseGen GitHub repository with the error messages.
