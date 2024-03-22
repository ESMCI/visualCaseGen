from ipywidgets import GridBox, ValueWidget, ToggleButtons, FloatText, Label, Layout
from traitlets import Unicode, validate, observe
from pathlib import Path

from ipyfilechooser import FileChooser

class FsurdatMatrix(GridBox, ValueWidget):
    """A widget for editing the fsurdat matrix consisting of LAI, SAI, hgt_top, and hgt_bot values."""

    def __init__(self):

        cw = '50px'

        ll = {'width':cw} # label layout
        el = {'width':cw} # entry layout
        
        gridbox_items = [
            Label(label, layout=ll) for label in ['var', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        ]

        gridbox_items.append(Label('LAI', layout=ll))
        self.lai= [FloatText('3',layout=el) for i in range(12)]
        gridbox_items.extend(self.lai)

        gridbox_items.append(Label('SAI', layout=ll))
        self.sai= [FloatText('1',layout=el) for i in range(12)]
        gridbox_items.extend(self.sai)

        gridbox_items.append(Label('hgt_top', layout=ll))
        self.hgt_top= [FloatText('1',layout=el) for i in range(12)]
        gridbox_items.extend(self.hgt_top)

        gridbox_items.append(Label('hgt_bot', layout=ll))
        self.hgt_bot= [FloatText('0.5',layout=el) for i in range(12)]
        gridbox_items.extend(self.hgt_bot)

        super().__init__(layout=Layout(grid_template_columns=f"repeat(13, {cw})",width='665px',padding='5px'))

        self.children = gridbox_items
        self.value = 'OK'
        self._disabled = False

    @observe('value')
    def _value_changed(self, change):
        if change['new'] != 'OK':
            # never allow value to change
            self.value = 'OK'
            self._property_lock = {"value": self.value}
            self._property_lock = {}
    
    @property
    def disabled(self):
        return self._disabled
    
    @disabled.setter
    def disabled(self, value):
        self._disabled = value
        for child in self.children:
            child.disabled = value


    
