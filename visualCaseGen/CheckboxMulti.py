import difflib
import ipywidgets as widgets
from traitlets import Int, Unicode, Tuple, Any, Dict, HasTraits, observe
from ipywidgets import trait_types
from visualCaseGen.visualCaseGen.OutHandler import handler as owh

class CheckboxMulti(widgets.VBox, HasTraits):

    value = trait_types.TypedTuple(trait=Any(), help="Selected values").tag(sync=True)
    index = trait_types.TypedTuple(trait=Int(), help="Selected indices").tag(sync=True)
    options = Any((),  help="Iterable of values, (label, value) pairs, or a mapping of {label: value} pairs that the user can select.")
    _property_lock = Dict() # the contents of this is not the same as those of the default widgets. This attribute is
                            # introduced in CheckboxMulti to capture value/index changes invoked at the front end only,
                            # similar to how the conventional _property_lock gets changed only via frontend changes.

    def __init__(self, options=None, value=None, description='', allow_multi_select=True):
        super().__init__()
        self.description = description # not displayed.
        self._allow_multi_select = allow_multi_select # if false, only a single options may be selected on the frontend.
                                                # multiple options may still be selected via the backend.
        self._select_multiple = False
        self._options = []
        self._options_indices = dict() #keys: option names, values: option indexes
        self._options_widgets = []
        self._tooltips_widgets = []
        self._options_vbox = widgets.VBox()
        self._searchbar = widgets.Text(placeholder='Sort by keys e.g., simple, CO2, ecosystem, etc.')
        self._init_selectmode()
        self.children = [
            widgets.HBox([self._searchbar, self._selectmode], layout=widgets.Layout(justify_content='space-between')),
            self._options_vbox]
        self._searchbar.observe(self._sort_opts_by_relevance, names='value')
        if options:
            self.set_trait('options',options)
        if value:
            self.set_trait('value',value)

    def _init_selectmode(self):
        self._selectmode = w = widgets.ToggleButtons(
            options=['single', 'multiple'], description='Selection:',
            tooltips=['The user is allowed to pick one option only. This is the safe mode.',
              'The user may select multiple options. Options compatibility NOT ensured. Use with caution.'],
            #icons=['shield-alt', 'exclamation-triangle']
            )
        self._selectmode.style.button_width='50px'
        self._selectmode.style.height='30px'
        self._selectmode.layout.visibility = 'hidden'

        @owh.out.capture()
        def selectmode_change(change):
            new_val = change['new']
            if new_val == 'single':
                self._select_multiple = False
                if len(self.value) > 1:
                    self.value = ()
            else:
                from IPython.display import display, HTML, Javascript
                warn_msg = \
                    """WARNING: visualCaseGen doesn't check the compatibility of multiple options. """\
                    """Use this mode with caution! Refer to the component documentation to check which options """\
                    """may be combined."""
                js = """<script>alert(" {} ");</script>""".format(warn_msg)
                display(HTML(js))
                self._select_multiple = True

        self._selectmode.observe(selectmode_change, names='value', type='change')

    def update_value(self,change):
        """ changes propagate from frontend (js checkboxes) to the backend (CheckboxMulti class)"""

        opt = change['owner'].description
        new_val = change['new']
        if new_val == True:
            if opt not in self.value:
                if self._select_multiple:
                    self.value += (opt,)
                else:
                    self.value = (opt,)
                # let the observers know that a frontend-invoked change was made:
                self._property_lock = {'changed_opt':opt}
        else:
            if opt in self.value:
                if self._select_multiple:
                    val_list = list(self.value)
                    val_list.remove(opt)
                    self.value = tuple(val_list)
                else:
                    self.value = ()
                # let the observers know that a frontend-invoked change was made:
                self._property_lock = {'changed_opt':opt}

        self.index = tuple([self._options_indices[opt] for opt in self.value])

    @observe('options')
    def _set_options(self, change):
        new_opts = change['new']
        self.value = ()

        # check if the number of options is the same as before. If so, reuse the
        # existing widgets. This improves the performance a lot. (e.g., when
        # changes occur only in the options name such as a status update)

        reuse_widgets = False
        if len(self._options) == len(new_opts):
                reuse_widgets = True

        self._options = new_opts
        self._options_indices = {new_opts[i]:i for i in range(len(new_opts))}
        self._search_list = ['{} := {}'.format(opt, '.') for opt in self._options]

        for opt_widget in self._options_widgets:
            opt_widget.unobserve(self.update_value, names='value', type='change')

        if reuse_widgets:
            for opt_ix in range(len(self._options)):
                opt = self._options[opt_ix]
                self._options_widgets[opt_ix].description = opt
                self._options_widgets[opt_ix].value = False
                self._tooltips_widgets[opt_ix].value = ''
        else:
            self._options_widgets = [widgets.Checkbox(description=opt, value=False,
                    layout=widgets.Layout(width='240px', left='-40px')) for opt in self._options]
            self._tooltips_widgets = [widgets.Label('',
                    layout={'width':'600px'}) for opt in self._options]

        for opt_widget in self._options_widgets:
            opt_widget.observe(self.update_value, names='value', type='change')

        if not reuse_widgets:
            self._display_options()

        if len(self._options) > 1 and self._allow_multi_select:
            self._selectmode.layout.visibility = 'visible'
        else:
            self._selectmode.value = 'single'
            self._selectmode.layout.visibility = 'hidden'

    @observe('value')
    def _propagate_value(self, change):
        """ changes propagate from the backend (CheckboxMulti) to children (i.e., actual checkboxes) """
        new_vals = change['new']
        # update checkboxes
        for i in range(len(self._options)):
            opt = self._options[i]
            opt_widget = self._options_widgets[i]

            if opt in new_vals:
                if opt_widget.value!=True:
                    opt_widget.value = True
            else:
                if opt_widget.value!=False:
                    opt_widget.value = False

        new_index = tuple([self._options_indices[opt] for opt in new_vals])
        if self.index != new_index:
            self.index = new_index

    @observe('index')
    def _propagate_index(self, change):
        """ changes propagate from the backend (CheckboxMulti) to children (i.e., actual checkboxes) """
        new_idxs = change['new']
        new_value = tuple([self._options[opt_ix] for opt_ix in new_idxs])
        if self.value != new_value:
            self.value = new_value


    def _display_options(self, options_list=None):
        rows = []
        if options_list:
            for opt in options_list:
                opt = opt.split(':=')[0].strip()
                opt_ix = self._options_indices[opt]
                rows.append(widgets.HBox([self._options_widgets[opt_ix], self._tooltips_widgets[opt_ix]]))
            self._options_vbox.children = tuple(rows)
        else:
            rows = [widgets.HBox([self._options_widgets[i], self._tooltips_widgets[i]]) for i in range(len(self._options))]
            self._options_vbox.children = tuple(rows)

    def _sort_opts_by_relevance(self,change):
        key = change['new']
        if key == '': # display all options
            self._display_options()
        else: # display filtered options
            narrowed_opts = difflib.get_close_matches(key, self._search_list, n=len(self._options), cutoff=0.0)
            self._display_options(narrowed_opts)

    @property
    def tooltips(self):
        raise NotImplementedError

    @tooltips.setter
    def tooltips(self, new_tooltips):
        assert len(new_tooltips) == len(self._options), "Tooltips length is not equal to options length."
        for opt_ix in range(len(self._options)):
            opt = self._options[opt_ix]
            self._tooltips_widgets[opt_ix].value = new_tooltips[opt_ix]
            self._search_list[opt_ix] = '{} := {}'.format(opt, new_tooltips[opt_ix])