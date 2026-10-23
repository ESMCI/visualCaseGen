"""Unit tests for visualCaseGen.user_nl_blocks: a tool's rerun replaces its own
user_nl entries and leaves everything else alone."""

from visualCaseGen import user_nl_blocks

TAG = "my_tool setup"
CREATION = "INPUTDIR = /inputdir/ocn\nNIGLOBAL = 10\n"
IC = ("Initial conditions", [("INIT_LAYERS_FROM_Z_FILE", "True")])
TIDES = ("Tides", [("TIDES", "True"), ("TIDE_M2", "True")])


def _keys(text):
    """The variables a user_nl file sets, in order, repeats included."""
    return [
        line.split("=", 1)[0].strip()
        for line in text.splitlines()
        if "=" in line and not line.lstrip().startswith("!")
    ]


def test_a_rerun_replaces_the_block(tmp_path):
    path = tmp_path / "user_nl_mom"
    path.write_text(CREATION)

    def run(*groups):
        edited = user_nl_blocks.strip(tmp_path, TAG)
        user_nl_blocks.write(
            "ic", "mom", list(groups), caseroot=tmp_path, ninst=1, tag=TAG
        )
        return edited

    run(IC, TIDES)
    once = path.read_text()
    assert run(IC, TIDES) == []  # the block was not edited by hand
    assert path.read_text() == once
    run(IC)
    assert _keys(path.read_text()) == [
        "INPUTDIR",
        "NIGLOBAL",
        "INIT_LAYERS_FROM_Z_FILE",
    ]


def test_a_variable_set_outside_the_blocks_is_left_out(tmp_path):
    """Whatever its case or spacing: MOM6 stops on a variable listed twice, and
    CDEPS reads "stream : key" like "stream:key" and applies the last line."""
    (tmp_path / "user_nl_mom").write_text("tides = False\n")
    (tmp_path / "user_nl_datm_streams").write_text("JRA.PREC : year_first = 2000\n")
    case = dict(caseroot=tmp_path, ninst=1, tag=TAG)
    user_nl_blocks.write("tides", "mom", [TIDES], **case)
    years = [("JRA.PREC:year_first", 2014), ("JRA.PREC:year_last", 2015)]
    user_nl_blocks.write("streams", "datm_streams", [(None, years)], **case)

    assert _keys((tmp_path / "user_nl_mom").read_text()) == ["tides", "TIDE_M2"]
    assert _keys((tmp_path / "user_nl_datm_streams").read_text()) == [
        "JRA.PREC : year_first",
        "JRA.PREC:year_last",
    ]


def test_strip_removes_only_this_tags_blocks(tmp_path):
    """The block below is laid out as write() lays it out; files that already
    hold blocks depend on that layout still being read."""
    ours = (
        "\n"
        "! >>> my_tool setup: ic [sha:b56ae51b] (rewritten on every call; "
        "set your own values outside this block)\n"
        "INIT_LAYERS_FROM_Z_FILE = True\n"
        "! <<< my_tool setup: ic\n"
    )
    path = tmp_path / "user_nl_mom"
    path.write_text(CREATION + ours)
    user_nl_blocks.write(
        "tides", "mom", [TIDES], caseroot=tmp_path, ninst=1, tag="other tool"
    )
    rest = path.read_text().replace(ours, "")

    assert user_nl_blocks.strip(tmp_path, TAG) == []
    assert path.read_text() == rest


def test_each_instance_file_gets_its_own_block(tmp_path):
    (tmp_path / "user_nl_mom_0002").write_text("INIT_LAYERS_FROM_Z_FILE = False\n")
    for _ in range(2):
        user_nl_blocks.strip(tmp_path, TAG)
        user_nl_blocks.write("ic", "mom", [IC], caseroot=tmp_path, ninst=2, tag=TAG)

    assert _keys((tmp_path / "user_nl_mom_0001").read_text()) == [
        "INIT_LAYERS_FROM_Z_FILE"
    ]
    assert (tmp_path / "user_nl_mom_0002").read_text() == (
        "INIT_LAYERS_FROM_Z_FILE = False\n"
    )
    assert not (tmp_path / "user_nl_mom").exists()


def test_restore_puts_back_what_snapshot_saw(tmp_path):
    (tmp_path / "user_nl_mom").write_text(CREATION)
    saved = user_nl_blocks.snapshot(tmp_path)
    case = dict(caseroot=tmp_path, ninst=1, tag=TAG)
    user_nl_blocks.write("ic", "mom", [IC], **case)
    user_nl_blocks.write("ice", "cice", [(None, [("ice_ic", "'default'")])], **case)

    user_nl_blocks.restore(tmp_path, saved)
    assert {p.name: p.read_text() for p in tmp_path.glob("user_nl_*")} == {
        "user_nl_mom": CREATION
    }
