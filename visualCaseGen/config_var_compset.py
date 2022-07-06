import logging
from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.config_var_str import ConfigVarStr
from traitlets import Unicode, validate

logger = logging.getLogger('\t'+__name__.split('.')[-1])

class ConfigVarCompset(ConfigVarStr):
    """ A specialized ConfigVar type for Compset"""
    
    @validate('value')
    def _validate_value(self, proposal):
        # Any COMPSET assignment is trivially valid, so don't do any validation here.
        new_val = proposal['value']
        return new_val

    @owh.out.capture()
    def _update_widget_value(self):

        if self.value == "":
            self._widget.value = "<p style='text-align:right'><b><i>compset: </i><font color='red'>not all component physics selected yet.</b></p>"
        else:
            self._widget.value = f"<p style='text-align:right'><b><i>compset: </i><font color='green'>{self.value}</b></p>"

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        # COMPSET widget cannot be changed from the frontend, so no need to implement this method.
        pass 