"""Tool-owned blocks in a case's ``user_nl_*`` files.

A tool that configures a case after it was created may run again on the same
case (a notebook cell rerun, or new settings), so the user_nl entries it
writes go inside marked blocks, one per owner (a part of the tool) and file::

    ! >>> <tag>: <owner> [sha:1a2b3c4d] (rewritten ...)
    ...
    ! <<< <tag>: <owner>

``tag`` names the tool and is the same on all of its blocks. The sha is a
hash of the block's lines as written, which ``strip`` uses to spot hand edits.

Every run first removes all of the tool's blocks (``strip``), then writes its
own (``write``), so the files end up as if only the latest run had happened.
Lines outside the blocks are left alone: what case creation wrote and
whatever the user added.

A variable the user sets outside the blocks takes precedence: ``write`` leaves
it out of the tool's block. Otherwise user_nl_mom would list it twice, which
stops the MOM6 build, and CICE, WW3 and CDEPS would take whichever line comes
last.

The marker lines are ``!`` comments, which MOM_interface's user_nl parser,
CIME's namelist parser and CDEPS's stream-mod parser all skip.

Every function is given the caseroot (and ``write`` the number of instances)
instead of reading ``cvars``, so several cases can be configured in one
process, and without the GUI.
"""

import hashlib
import re
from pathlib import Path

_NOTE = "(rewritten on every call; set your own values outside this block)"


def _begin(tag):
    return f"! >>> {tag}: "


def _end(tag):
    return f"! <<< {tag}: "


def _sha(body):
    return hashlib.sha1(body.encode()).hexdigest()[:8]


def _files(caseroot, model, ninst):
    """The user_nl files append_user_nl writes for this model."""
    if ninst is None or ninst == 1:
        return [caseroot / f"user_nl_{model}"]
    return [
        caseroot / f"user_nl_{model}_{str(i).zfill(4)}" for i in range(1, ninst + 1)
    ]


def _parse(lines, path, tag):
    """[(owner, sha, begin, end)] line indices of the blocks in ``lines``."""
    # Any owner write() accepts, spaces included, so that strip() finds every
    # block write() wrote.
    begin_re = re.compile(re.escape(_begin(tag)) + r"(.*?) \[sha:([0-9a-f]+)\]")
    blocks = []
    i = 0
    while i < len(lines):
        match = begin_re.match(lines[i])
        if match:
            owner, sha = match.groups()
            end_line = f"{_end(tag)}{owner}"
            end = next(
                (
                    j
                    for j in range(i + 1, len(lines))
                    if lines[j].rstrip("\n") == end_line
                ),
                None,
            )
            if end is None:
                raise RuntimeError(
                    f"{path}, line {i + 1}: the '{owner}' block has no "
                    f"'{end_line}' line, so it's unclear where the block ends. "
                    "Restore that line, or delete the block, and try again."
                )
            blocks.append((owner, sha, i, end))
            i = end
        i += 1
    return blocks


def _key(name):
    """A variable name as compared across lines: case-insensitive, and with no
    whitespace, since CDEPS reads "stream : key" and "stream:key" alike."""
    return "".join(name.split()).lower()


def _set_keys(lines, path, tag):
    """The (normalized) variables set outside the ``tag`` blocks, and
    {variable: owner} for those set inside them."""
    owners = [None] * len(lines)
    for owner, _, begin, end in _parse(lines, path, tag):
        owners[begin : end + 1] = [owner] * (end + 1 - begin)
    outside, inside = set(), {}
    for line, owner in zip(lines, owners):
        text = line.strip()
        if text.startswith("!") or "=" not in text:
            continue
        key = _key(text.split("=", 1)[0])
        if owner is None:
            outside.add(key)
        else:
            inside[key] = owner
    return outside, inside


def _read_lines(path):
    return path.read_text().splitlines(keepends=True) if path.exists() else []


def _log(path, kept, skipped, tag):
    """Print what ``write`` adds to ``path``, laid out as append_user_nl
    prints it, and the variables it left out."""
    if kept:
        print(f"Adding parameter changes to {path.name}:\n")
    for comment, pairs in kept:
        if comment:
            print(f"  ! {comment}")
        for var, val in pairs:
            print(f"  {var} = {val}")
        print("")
    for var in skipped:
        print(
            f"  ! {var}: set outside the '{tag}' blocks in {path.name}; "
            "that value is kept"
        )


def snapshot(caseroot):
    """The contents of every user_nl file in ``caseroot``, for ``restore``.

    Keyed by absolute path, so that ``restore`` matches them however its
    caseroot is spelled, and wherever the working directory has moved to.
    """
    return {
        path: path.read_text()
        for path in Path(caseroot).resolve().glob("user_nl_*")
        if path.is_file()
    }


def restore(caseroot, contents):
    """Put the user_nl files back as ``snapshot`` found them, so that a run
    that fails part-way leaves them as they were."""
    for path in Path(caseroot).resolve().glob("user_nl_*"):
        if path.is_file() and path not in contents:
            path.unlink()
    for path, text in contents.items():
        path.write_text(text)


def strip(caseroot, tag):
    """Remove every ``tag`` block from the user_nl files in ``caseroot``.

    Returns ``[(file name, owner, body lines)]`` for the blocks whose contents
    differ from what ``write`` wrote, i.e. that were edited by hand, so that
    ``report_edits`` can say what was replaced.
    """
    edited = []
    for path in sorted(Path(caseroot).glob("user_nl_*")):
        if not path.is_file():
            continue
        lines = _read_lines(path)
        blocks = _parse(lines, path, tag)
        if not blocks:
            continue
        keep = [True] * len(lines)
        for owner, sha, begin, end in blocks:
            body = lines[begin + 1 : end]
            if _sha("".join(body)) != sha:
                edited.append((path.name, owner, body))
            keep[begin : end + 1] = [False] * (end + 1 - begin)
            # The blank line write() puts before each block.
            if begin > 0 and keep[begin - 1] and not lines[begin - 1].strip():
                keep[begin - 1] = False
        path.write_text("".join(line for line, k in zip(lines, keep) if k))
    return edited


def write(owner, model, groups, *, caseroot, ninst, tag):
    """Write ``owner``'s block into ``caseroot``'s user_nl_<model> (each of
    the ``ninst`` instances' files).

    ``groups`` is ``[(comment or None, [(var, val), ...]), ...]``; the block
    holds them as consecutive append_user_nl calls would write them, and the
    log shows them the same way. Variables the file already sets outside the
    blocks are left out (see the module docstring). A variable another of the
    ``tag`` blocks already sets raises a ValueError: the file would list it
    twice, and which of the two values wins would depend on the call order.
    """
    per_file = []
    for path in _files(Path(caseroot), model, ninst):
        lines = _read_lines(path)
        outside, inside = _set_keys(lines, path, tag)
        for _, pairs in groups:
            for var, _ in pairs:
                if _key(var) in inside:
                    raise ValueError(
                        f"{path}: '{owner}' sets {var}, which the "
                        f"'{inside[_key(var)]}' block already sets. A variable "
                        f"can be in only one of the '{tag}' blocks."
                    )
        kept = []
        for comment, pairs in groups:
            pairs = [(var, val) for var, val in pairs if _key(var) not in outside]
            if pairs:
                kept.append((comment, pairs))
        skipped = [
            var for _, pairs in groups for var, _ in pairs if _key(var) in outside
        ]
        per_file.append((path, lines, kept, skipped))

    # Every file is parsed before any is written, so a malformed one changes
    # nothing.
    for path, lines, kept, skipped in per_file:
        _log(path, kept, skipped, tag)
        if not kept:
            continue
        body = "".join(
            (f"\n! {comment}\n" if comment else "")
            + "".join(f"{var} = {val}\n" for var, val in pairs)
            for comment, pairs in kept
        )
        separator = "" if not lines or lines[-1].endswith("\n") else "\n"
        with open(path, "a") as f:
            f.write(
                f"{separator}\n{_begin(tag)}{owner} [sha:{_sha(body)}] {_NOTE}\n"
                f"{body}{_end(tag)}{owner}\n"
            )


def report_edits(caseroot, edited, tag):
    """Warn about the hand edits ``strip`` found, once the blocks have been
    rewritten: the lines each edited block lost, and those it got back."""
    for name, owner, body in edited:
        path = Path(caseroot) / name
        lines = _read_lines(path)
        new = [
            line.strip()
            for block_owner, _, begin, end in _parse(lines, path, tag)
            if block_owner == owner
            for line in lines[begin + 1 : end]
            if line.strip()
        ]
        old = [line.strip() for line in body if line.strip()]
        discarded = [line for line in old if line not in new]
        restored = [line for line in new if line not in old]
        if not discarded and not restored:
            continue
        print(
            f"WARNING: {name} was edited inside the '{tag}: {owner}' block, "
            "which is rewritten on every call."
        )
        for label, changed in (("Discarded", discarded), ("Written back", restored)):
            if changed:
                print(f"  {label}:")
                for line in changed:
                    print(f"    {line}")
        print(
            f"  Set your own values outside the '! >>> {tag}' blocks instead: "
            "those are kept, and take precedence over the values in the blocks."
        )
