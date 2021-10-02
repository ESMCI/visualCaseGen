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

    def __init__(self, value=None, options=None, description='', disabled=False, placeholder='', allow_multi_select=True):
        super().__init__()

        #options
        self._options = []
        self._options_indices = dict() #keys: option names, values: option indexes
        self._options_widgets = []
        self._tooltips = []
        self._tooltips_widget = widgets.HTML(value='', placeholder='', description='')
        self._options_hbox = widgets.HBox()

        # general CheckboxMulti widget configuration
        self.description = description # not displayed.
        self._disabled = disabled
        self._placeholder = placeholder
        self._select_multiple = False
        self._allow_multi_select = allow_multi_select # if false, only a single options may be selected on the frontend.
                                                # multiple options may still be selected via the backend.

        # auxiliary widgets: searchbar and selection mode switch
        self._searchbar = widgets.Text(placeholder='Type in keywords to sort the options', layout={'margin':'3px'})
        self._init_selectmode()
        self._searchbar.observe(self._sort_opts_by_relevance, names='value')

        # construct the widget display:
        self._construct_display()

        if options:
            self.set_trait('options',options)
        if value:
            self.set_trait('value',value)

    def _construct_display(self):
        # set VBox children:
        if self._disabled:
            self.children = [widgets.Label(self._placeholder)]
        else:
            if len(self._options) < 2:
                self._searchbar.value = ''
                self.children = [self._options_hbox]
            else:
                if self._allow_multi_select:
                    self.children = [
                        widgets.HBox([  self._searchbar,
                                        self._selectmode],
                                        layout=widgets.Layout(justify_content='space-between')),
                        self._options_hbox]
                else:
                    self.children = [self._searchbar, self._options_hbox]

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, disabled):
        if self._disabled != disabled:
           self._disabled = disabled
           self._construct_display()

    @property
    def placeholder(self):
        return self._placeholder

    @placeholder.setter
    def placeholder(self, placeholder):
        self._placeholder = placeholder
        if self._disabled:
            self._construct_display()

    def _init_selectmode(self):
        self._selectmode = widgets.ToggleButtons(
            options=['single', 'multi'], description='Selection:',
            tooltips=['The user is allowed to pick one option only. This is the safe mode.',
              'The user may select multiple options. Options compatibility NOT ensured. Use with caution.'],
            #icons=['shield-alt', 'exclamation-triangle']
            )
        self._selectmode.style.button_width='40px'
        self._selectmode.style.height='30px'

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
                self._property_lock = {'value':self.value}
        else:
            if opt in self.value:
                if self._select_multiple:
                    val_list = list(self.value)
                    val_list.remove(opt)
                    self.value = tuple(val_list)
                else:
                    self.value = ()
                # let the observers know that a frontend-invoked change was made:
                self._property_lock = {'value':self.value}

        self.index = tuple([self._options_indices[opt] for opt in self.value])
        self._property_lock = {}

    @observe('options')
    def _set_options(self, change):
        new_opts = change['new']
        self.value = ()

        # check if the number of options is the same as before. If so, reuse the
        # existing widgets. This improves the performance a lot. (e.g., when
        # changes occur only in the options name such as a status update)

        reuse_widgets = False
        status_change_only = False
        if len(self._options) == len(new_opts):
                reuse_widgets = True
                status_change_only = [opt[1:] for opt in self._options] == [opt[1:] for opt in new_opts]

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
                if not status_change_only:
                    self._tooltips[opt_ix] = ''
        else:
            self._options_widgets = [widgets.Checkbox(description=opt, value=False,
                    layout=widgets.Layout(width='240px', left='-40px', margin='0px')) for opt in self._options]
            self._tooltips = ['']*len(self._options)

        for opt_widget in self._options_widgets:
            opt_widget.observe(self.update_value, names='value', type='change')

        if not reuse_widgets:
            self._construct_display()
            self._display_options()

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

        options_widgets_display = []
        tooltips_display = []
        if options_list:
            for opt in options_list:
                opt = opt.split(':=')[0].strip()
                opt_ix = self._options_indices[opt]
                options_widgets_display.append(self._options_widgets[opt_ix])
                tooltips_display.append(self._tooltips[opt_ix])
        else:
            options_widgets_display = self._options_widgets
            tooltips_display = self._tooltips

        self._tooltips_widget.value = '<style>p{white-space: nowrap}</style> <p>'+'<br>'.join(tooltips_display)+'<br></p>'

        self._options_hbox.children = tuple([
            widgets.VBox(options_widgets_display),
            widgets.VBox((self._tooltips_widget,), layout={'width':'540px','overflow_y': 'hidden'})
        ])

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
        self._tooltips = new_tooltips
        self._search_list = ['{} := {}'.format(self._options[i], new_tooltips[i]) \
            for i in range(len(self._options))]
        self._display_options()