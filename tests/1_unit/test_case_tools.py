from ProConPy.config_var import cvars
from visualCaseGen.custom_widget_types.case_tools import append_user_nl, xmlchange


def test_case_tools_write_into_the_given_caseroot(tmp_path, monkeypatch):
    """Given a caseroot (and ninst), xmlchange and append_user_nl act on that
    case without the CASEROOT/NINST config variables, and the xmlchange value
    reaches ./xmlchange as a single argument."""
    monkeypatch.delitem(cvars, "CASEROOT", raising=False)
    monkeypatch.delitem(cvars, "NINST", raising=False)

    # Stand-in for the case's ./xmlchange: it records its arguments in the
    # directory it runs in.
    stub = tmp_path / "xmlchange"
    stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > xmlchange_args\n')
    stub.chmod(0o755)

    xmlchange("CASE_DESC", "two words", caseroot=tmp_path)
    assert (tmp_path / "xmlchange_args").read_text() == "CASE_DESC=two words\n"

    append_user_nl("mom", [("DT", "900.0")], True, caseroot=tmp_path, ninst=2)
    assert (tmp_path / "user_nl_mom_0002").read_text() == "DT = 900.0\n"
