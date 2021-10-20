from visualCaseGen.visualCaseGen.gui import GUI
try:
    GUI().display()._ipython_display_()
except AttributeError:
    GUI().display()._repr_mimebundle_()