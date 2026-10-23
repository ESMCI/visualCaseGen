"""Plan the stream year settings that align CDEPS data streams with a run.

CDEPS hardcodes ``year_align=1`` and the full year span for every JRA stream in
``stream_definition_{datm,drof}.xml``, and none of the JRA, NYF or ERA5 stream
entries reads the ``DATM_YR_ALIGN``/``_START``/``_END`` xml variables (only
the land-forcing and CPLHIST streams do). So a JRA case silently reads an
arbitrary data year, and ``xmlchange`` cannot fix it. The only lever CDEPS
offers is ``user_nl_<comp>_streams``.

Narrowing the file list matters as much as the alignment: the ``<datafiles>``
list is expanded from the stream definition's own year tags *before* user mods
are merged, so retagging the years alone still leaves all 59 JRA files
enumerated, and CDEPS reads the time axis of each one in turn until it reaches
the year it needs.

``plan_stream_years`` only computes the settings; it writes nothing. To apply a
"configured" plan, write one ``<stream>:<key> = <value>`` line per setting to
``user_nl_<comp>_streams``, joining ``datafiles`` with commas.
"""

from visualCaseGen import cdeps_streams


def plan_stream_years(
    cesmroot, component, mode, case, start_year, end_year, *, padding=1, narrow=True
):
    """Work out the stream year settings for one component, or why there are none.

    Parameters
    ----------
    cesmroot : str or Path
        The CESM root directory (the one holding cime/ and components/cdeps/).
    component : str
        The CDEPS data component, e.g., "datm" or "drof".
    mode : str
        The component's stream set, i.e., the case's DATM_MODE or DROF_MODE.
    case : CIME Case or similar
        Only its get_value method is used, to expand $-variables such as
        $DIN_LOC_ROOT in the stream definitions.
    start_year, end_year : int
        The first and last model years of the run.
    padding : int, optional
        Extra years of forcing to keep on either side of the run.
    narrow : bool, optional
        If True, also restrict each stream's datafiles to the years kept.

    Returns
    -------
    dict
        ``{"status": "configured", "mode": mode, "streams": {name: settings}}``,
        where settings holds year_first, year_last, year_align and, if narrow,
        datafiles (a list of paths). Otherwise ``{"status": "skipped",
        "reason": str}``: a component that cannot be aligned is reported
        rather than raised, so the caller can leave it at its CDEPS defaults.
    """
    names = cdeps_streams.stream_names(cesmroot, component, mode)
    if not names:
        return {"status": "skipped", "reason": f"no streams defined for {mode}"}

    streams = {}
    for name in names:
        avail_first, avail_last = cdeps_streams.coverage(
            cesmroot, component, name, case
        )
        # Single-year streams are climatologies (CORE2_NYF is 1/1/1, the
        # CORE_RYF*_JRA repeat years are e.g. 1961/1961). There is no
        # alignment to get right and no files to narrow.
        if avail_first == avail_last:
            return {
                "status": "skipped",
                "reason": f"{mode} is a single-year climatology",
            }
        if start_year < avail_first or end_year > avail_last:
            return {
                "status": "skipped",
                "reason": (
                    f"run years {start_year}-{end_year} fall outside the "
                    f"{avail_first}-{avail_last} covered by {mode}"
                ),
            }

        # year_align == year_first makes the data year equal the model year
        # for every year in range: dYear = yrFirst + modulo(mYear - yrFirst, n).
        # The extra leading year is needed to interpolate at the run start.
        year_first = max(avail_first, start_year - 1 - padding)
        year_last = min(avail_last, end_year + padding)
        streams[name] = {
            "year_first": year_first,
            "year_last": year_last,
            "year_align": year_first,
        }
        if narrow:
            streams[name]["datafiles"] = cdeps_streams.datafiles(
                cesmroot, component, name, year_first, year_last, case
            )
    return {"status": "configured", "mode": mode, "streams": streams}
