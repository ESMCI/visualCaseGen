from IPython.display import display, HTML

def alert_warning(msg):
    js = """<script>alert("WARNING: {} ");</script>""".format(msg)
    display(HTML(js))

def alert_error(msg):
    js = "<script>alert('ERROR: {}');</script>".format(msg)
    display(HTML(js))
