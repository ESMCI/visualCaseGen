""" Logging Output Handler Module """

import logging
import sys
import ipywidgets as widgets

logger = logging.getLogger(__name__)


class _NameStrippingFormatter(logging.Formatter):
    """Formatter that drops the whitespace some logger names are padded with."""

    def format(self, record):
        name = record.name
        record.name = name.strip()
        try:
            return super().format(record)
        finally:
            record.name = name


def _console_handlers():
    """INFO and below to stdout, WARNING and above to stderr, so that notebooks
    (which show stderr on a red background) only flag actual warnings."""
    formatter = _NameStrippingFormatter("%(levelname)s [%(name)s] %(message)s")
    to_stdout = logging.StreamHandler(sys.stdout)
    to_stdout.addFilter(lambda record: record.levelno < logging.WARNING)
    to_stderr = logging.StreamHandler(sys.stderr)
    to_stderr.setLevel(logging.WARNING)
    for handler in (to_stdout, to_stderr):
        handler.setFormatter(formatter)
    return [to_stdout, to_stderr]


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
        logging.basicConfig(level=logging.DEBUG, handlers=_console_handlers())
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
