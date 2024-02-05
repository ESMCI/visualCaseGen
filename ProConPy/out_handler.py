""" Logging Output Handler Module """

import logging
import ipywidgets as widgets

logger = logging.getLogger(__name__)


class OutHandler(logging.Handler):
    """Custom logging handler sending logs to an output widget"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = {
            #'width': '100%',
            #'height': '160px',
            "border": "1px solid black"
        }
        self.out = widgets.Output(layout=layout)
        logging.basicConfig(level=logging.DEBUG, datefmt="%I:%M:%S")
        self.set_verbosity(verbose=False)

    def emit(self, record):
        """Overload of logging.Handler method"""
        formatted_record = self.format(record)
        new_output = {
            "name": "stdout",
            "output_type": "stream",
            "text": formatted_record + "\n",
        }
        self.out.outputs = (new_output,) + self.out.outputs

    def clear_logs(self):
        """Clear the current logs"""
        self.out.clear_output()

    def set_verbosity(self, verbose=False):
        """Set logging verbosity level. By default, the level is set to INFO.

        Parameters
        ----------
        verbose : bool, optional
            If True, logging level is set to DEBUG.
        """
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
        for module in ["CIME.XML", "CIME.utils", "CIME.config", "Comm"]:
            logger_temp = logging.getLogger(module)
            logger_temp.setLevel(logging.INFO)


handler = OutHandler()
logger.addHandler(handler)
