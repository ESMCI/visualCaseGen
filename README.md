# visualCaseGen - Quickstart

## 0. Prerequisites:
Make sure that you have the following packages installed and CESM ported. Note: Below instructions are for Mac/Linux users.
- Jupyter**Lab**, ipywidgets, PyYAML

## 1. Installation:
Check out the specific CESM version that includes visualCaseGen by running the following commands in a terminal:

```
git clone https://github.com/alperaltuntas/cesm.git -b simpler_models
(cd cesm; ./manage_externals/checkout_externals -o)
```

Note: To be able to run the GUI on cheyenne/casper JupyterLab, run the above command within your glade home directory (or create a symbolic link to the cesm sandbox at your home directory).

## 2. Running the GUI

- Launch JupyterLab and open the following notebook:
```cesm/cime/scripts/GUI.ipynb```

- Execute the first (and only) cell in the notebook, which should look like:
```
from visualCaseGen.visualCaseGen.GUI import GUI
GUI().display()
```
