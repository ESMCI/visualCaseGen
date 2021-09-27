import difflib
import ipywidgets as widgets
from traitlets import Int, Unicode, Tuple, Any, HasTraits, observe
from ipywidgets import trait_types

class CheckboxMulti(widgets.VBox, HasTraits):

    value = trait_types.TypedTuple(trait=Any(), help="Selected values")
    options = Any((),
                  help="Iterable of values, (label, value) pairs, or a mapping of {label: value} pairs that the user can select.")

    def __init__(self, options=None, value=None):
        super().__init__()
        self._options_indices = dict() #keys: option names, values: option indexes
        self._options_widgets = dict() #keys: option names, values: option widgets
        self._options_vbox = widgets.VBox(layout={'overflow': 'scroll'})
        self._searchbar = widgets.Text(placeholder='Type in search keys e.g., simple, CO2, etc.')
        self.children = [self._searchbar, self._options_vbox]
        self._searchbar.observe(self._sort_opts_by_relevance, names='value')
        if options:
            self.set_trait('options',options)
        if value:
            self.set_trait('value',value)
        self._tooltips_widgets = dict()

    def update_value(self,change):
        """ changes propagate from children (i.e., actual checkboxes) to the parent i.e., backend (CheckboxMulti)"""
        opt = change['owner'].description
        new_val = change['new']
        if new_val == True:
            if opt not in self.value:
                self.value += (opt,)
        else:
            if opt in self.value:
                val_list = list(self.value)
                val_list.remove(opt)
                self.value = tuple(val_list)

    @observe('options')
    def _set_options(self, change):
        new_opts = change['new']
        self.value = ()
        self._options_indices = {new_opts[i]:i for i in range(len(new_opts))}
        self._construct_options_widgets()
        #return self._options

    def _construct_options_widgets(self):

        for opt, opt_widget in self._options_widgets.items():
            opt_widget.unobserve(self.update_value, names='value', type='change')

        self._search_list = ['{} := {}'.format(opt, '.') for opt in self._options_indices] 
        self._options_widgets = {opt: widgets.Checkbox(description=opt, value=False) for opt in self._options_indices}
        self._tooltips_widgets = {opt: widgets.Label('') for opt in self._options_indices}

        for opt, opt_widget in self._options_widgets.items():
            opt_widget.observe(self.update_value, names='value', type='change')

        self._display_options()

    @observe('value')
    def _propagate_value(self, change):
        """ changes propagate from the backend (CheckboxMulti) to children (i.e., actual checkboxes) """
        new_vals = change['new']
        # update checkboxes
        for opt, widget in self._options_widgets.items():
            if opt in new_vals:
                if widget.value!=True:
                    widget.value = True
            else:
                if widget.value!=False:
                    widget.value = False

    def _display_options(self, options_list=None):
        rows = []
        if options_list:
            for opt in options_list:
                opt = opt.split(':=')[0].strip()
                #opt_ix = self._options_indices[opt]
                opt_widget = self._options_widgets[opt]
                rows.append(widgets.HBox([opt_widget, self._tooltips_widgets[opt]]))
            self._options_vbox.children = tuple(rows)
        else:
            for opt, opt_widget in self._options_widgets.items():
                #opt_ix = self._options_indices[opt]
                rows.append(widgets.HBox([opt_widget, self._tooltips_widgets[opt]]))
            self._options_vbox.children = tuple(rows)

    def _sort_opts_by_relevance(self,change):
        key = change['new']
        if key == '': # display all options
            self._display_options()
        else: # display filtered options
            #narrowed_opts = difflib.get_close_matches(key, self._options_indices.keys(), n=len(self._options_indices), cutoff=0.3)
            narrowed_opts = difflib.get_close_matches(key, self._search_list, n=len(self._options_indices), cutoff=0.05)
            self._display_options(narrowed_opts)

    @property
    def tooltips(self):
        raise NotImplementedError

    @tooltips.setter
    def tooltips(self, new_tooltips):
        assert len(new_tooltips) == len(self._options_indices), "Tooltips length is not equal to options length."
        self._search_list = [None]*len(self._options_indices)
        for opt, opt_ix in self._options_indices.items():
            self._tooltips_widgets[opt].value = new_tooltips[opt_ix]
            self._search_list[opt_ix] = '{} := {}'.format(opt, new_tooltips[opt_ix])
