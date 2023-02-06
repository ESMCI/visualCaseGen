from IPython.display import display, HTML

def alert_warning(msg):
    js = f"""<script>alert("WARNING: {msg} ");</script>"""
    display(HTML(js))

def alert_error(msg):
    js = f"<script>alert('ERROR: {msg}');</script>"
    display(HTML(js))
