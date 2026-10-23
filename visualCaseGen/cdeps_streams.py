"""Read CDEPS stream definitions through CIME's own parsers.

These are thin wrappers over ``StreamCDEPS`` and ``NamelistDefinition`` rather
than XML parsing of our own, so that the stream list and the expanded file
paths stay identical to what the CDEPS ``buildnml`` would generate. That
matters for streams whose files carry more than one datestamp: JRA v1.5 splits
1958-2023 across four ``<file>`` entries stamped 210504/220505/230718/240531,
and a hand-rolled expansion would silently emit paths that do not exist.

``coverage`` and ``datafiles`` call private ``StreamCDEPS`` helpers
(``_get_stream_first_and_last_dates``, ``_resolve_values``, ``_sub_paths``).
Every such call is kept in this module, so a CDEPS change that breaks them
needs fixing in one place.
"""

import os
import sys


def _cdeps_root(cesmroot):
    return os.path.join(str(cesmroot), "components", "cdeps")


def _component_config(cesmroot, component):
    return os.path.join(_cdeps_root(cesmroot), component, "cime_config")


def _add_to_path(directory):
    if directory not in sys.path:
        sys.path.append(directory)


def _ensure_cime(cesmroot):
    """Put CIME on sys.path.

    CIME_interface normally does this already, but doing it here too lets
    this module be used (and tested) without first constructing a
    CIME_interface.
    """
    _add_to_path(os.path.join(str(cesmroot), "cime"))


def _streams(cesmroot, component):
    """A StreamCDEPS object for ``component`` ("datm" or "drof").

    Rebuilt on every call rather than memoized here: CIME's ``GenericXML``
    keeps its own cache of parsed trees, so repeated construction costs
    well under a millisecond.
    """
    _ensure_cime(cesmroot)
    shared_config = os.path.join(_cdeps_root(cesmroot), "cime_config")
    # stream_cdeps.py is a loose module in the CDEPS config dir, not a package.
    _add_to_path(shared_config)
    from stream_cdeps import StreamCDEPS

    return StreamCDEPS(
        os.path.join(
            _component_config(cesmroot, component),
            f"stream_definition_{component}.xml",
        ),
        os.path.join(shared_config, "stream_definition_v2.0.xsd"),
    )


def stream_names(cesmroot, component, mode):
    """The stream names active for a DATM_MODE/DROF_MODE, in buildnml's order.

    The mode-to-streams mapping is matched by regex on the mode name, so this
    cannot be replaced by prefixing: CORE_IAF_JRA_1p5_2023 yields streams named
    CORE_IAF_JRA_1p5_2023.GCGCS.PREC, and the DROF mode IAF_JRA yields
    rof.iaf_jra.
    """
    _ensure_cime(cesmroot)
    from CIME.XML.namelist_definition import NamelistDefinition

    nmldef = NamelistDefinition(
        os.path.join(
            _component_config(cesmroot, component),
            f"namelist_definition_{component}.xml",
        )
    )
    nmldef.set_nodes()
    return nmldef.get_default_value(
        "streamslist", attribute={f"{component}_mode": mode}
    )


def _stream_entry(cesmroot, component, stream_name):
    streams = _streams(cesmroot, component)
    for node in streams.get_children("stream_entry"):
        if streams.get(node, "name") == stream_name:
            return streams, node
    raise KeyError(f"No stream_entry named {stream_name} in {component}")


def coverage(cesmroot, component, stream_name, cime_case):
    """The (year_first, year_last) the stream definition itself declares."""
    streams, node = _stream_entry(cesmroot, component, stream_name)
    return streams._get_stream_first_and_last_dates(node, cime_case)


def datafiles(cesmroot, component, stream_name, year_first, year_last, cime_case):
    """Resolved file paths covering [year_first, year_last].

    Mirrors the ``stream_datafiles`` branch of ``StreamCDEPS.create_stream_xml``:
    each ``<file>`` contributes only the years its own first_year/last_year
    attributes cover, so multi-datestamp streams resolve correctly.
    """
    streams, node = _stream_entry(cesmroot, component, stream_name)
    paths = []
    for child in streams.get_children("stream_datafiles", root=node):
        for entry in streams.get_children(root=child):
            template = streams._resolve_values(cime_case, entry.xml_element.text)
            attrib = entry.xml_element.attrib
            if "first_year" not in attrib or "last_year" not in attrib:
                paths.append(template.strip())
                continue
            first = max(
                int(streams._resolve_values(cime_case, attrib["first_year"])),
                year_first,
            )
            last = min(
                int(streams._resolve_values(cime_case, attrib["last_year"])),
                year_last,
            )
            if first > last:
                continue
            expanded = streams._sub_paths(
                stream_name,
                template,
                first,
                last,
                int(attrib.get("filename_advance_days", 0)),
            )
            paths += [line for line in expanded.strip().split("\n") if line]
    return paths
