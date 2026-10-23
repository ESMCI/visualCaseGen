"""Tests for planning CDEPS stream years (visualCaseGen.stream_years).

These read the real CDEPS stream definitions from the CESM tree that the other
integration tests use; no inputdata is needed. The exact file paths asserted
below double as a guard on the private CDEPS helpers that cdeps_streams calls,
so a CESM update that changes them fails here rather than silently producing
paths that do not exist.
"""

import pytest

from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.stream_years import plan_stream_years


class FakeCase:
    """Stands in for a CIME Case: plan_stream_years only calls get_value."""

    def get_value(self, name):
        return {"DIN_LOC_ROOT": "/inputdata"}.get(name)


def test_multi_year_streams_are_aligned_around_the_run():
    """A 2021 run keeps 2019-2022 (a lead-in year, plus one year of padding on
    each side), aligns the data year with the model year, and narrows each
    stream's files to those years, each year carrying its own datestamp."""
    plan = plan_stream_years(
        CIME_interface().srcroot,
        "datm",
        "CORE_IAF_JRA_1p5_2023",
        FakeCase(),
        2021,
        2021,
    )

    assert plan["status"] == "configured"
    assert len(plan["streams"]) == 8
    for settings in plan["streams"].values():
        assert settings["year_first"] == settings["year_align"] == 2019
        assert settings["year_last"] == 2022
    assert plan["streams"]["CORE_IAF_JRA_1p5_2023.GCGCS.PREC"]["datafiles"] == [
        f"/inputdata/ocn/jra55/v1.5_noleap/JRA.v1.5.prec.TL319.{year}.{stamp}.nc"
        for year, stamp in [
            (2019, 210504),
            (2020, 210504),
            (2021, 220505),
            (2022, 230718),
        ]
    ]


@pytest.mark.parametrize(
    "mode, year, reason",
    [
        ("CORE2_NYF", 2000, "single-year climatology"),
        ("CORE_IAF_JRA", 2020, "fall outside the 1958-2016"),
    ],
)
def test_unalignable_streams_are_skipped(mode, year, reason):
    """A repeating single year has nothing to align, and a run outside the
    stream's years cannot be aligned with real data. Both are reported instead
    of planned, so the case keeps its CDEPS defaults."""
    plan = plan_stream_years(
        CIME_interface().srcroot, "datm", mode, FakeCase(), year, year
    )
    assert plan["status"] == "skipped"
    assert reason in plan["reason"]
