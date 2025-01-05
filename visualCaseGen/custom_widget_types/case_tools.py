from pathlib import Path
import subprocess

from visualCaseGen.custom_widget_types.dummy_output import DummyOutput

COMMENT = "\033[01;96m"  # bold, cyan
RESET = "\033[0m"


def run_case_setup(caseroot, do_exec, is_non_local=False, out=None):
    """Run the case.setup script to set up the case instance.
    
    Parameters
    ----------
    caseroot : Path
        The path to the case directory.
    do_exec : bool
        If True, execute the commands. If False, only print them.    
    is_non_local : bool, optional
        If True, the case has been created on a machine different from the one
        that runs visualCaseGen.
    """

    # Run ./case.setup
    cmd = "./case.setup"
    if is_non_local:
        cmd += " --non-local"

    out = DummyOutput() if out is None else out
    with out:
        print(
            f"{COMMENT}Running the case.setup script with the following command:{RESET}\n"
        )
        print(f"{cmd}\n")
    if do_exec:
        runout = subprocess.run(cmd, shell=True, capture_output=True, cwd=caseroot)
        if runout.returncode != 0:
            raise RuntimeError(f"Error running {cmd}.")

def append_user_nl(user_nl_filename, var_val_pairs, caseroot, do_exec, comment=None, log_title=True, out=None):
    """Apply changes to a given user_nl file.
    
    Parameters
    ----------
    user_nl_filename : str
        The name of the user_nl file to modify.
    var_val_pairs : list of tuples
        A list of tuples, where each tuple contains a variable name and its value.
    caseroot: Path or str
        The path to the case directory
    do_exec : bool
        If True, execute the commands. If False, only print them.
    comment : str, optional
        A comment to print before the changes.
    log_title: bool, optional
        If True, print the log title "Adding parameter changes to user_nl_filename".
    out : Output, optional
        The output widget to use for displaying log messages
    """

    # confirm var_val_pairs is a list of tuples:
    assert isinstance(var_val_pairs, list)
    assert all(isinstance(pair, tuple) for pair in var_val_pairs)

    # Print the changes to the user_nl file:
    out = DummyOutput() if out is None else out
    with out:
        if log_title:
            print(f"{COMMENT}Adding parameter changes to {user_nl_filename}:{RESET}\n")
        if comment:
            print(f"  ! {comment}")
        for var, val in var_val_pairs:
            print(f"  {var} = {val}")
        print("")
    
    if not do_exec:
        return
    
    # Apply the changes to the user_nl file:
    with open(Path(caseroot) / user_nl_filename, "a") as f:
        if comment:
            f.write(f"\n! {comment}\n")
        for var, val in var_val_pairs:
            f.write(f"{var} = {val}\n")


def xmlchange(var, val, caseroot, do_exec=True, is_non_local=False, out=None):
    """Apply custom xml changes to the case.
    
    Parameters
    ----------
    caseroot : Path
        The path to the case directory.
    do_exec : bool
        If True, execute the commands. If False, only print them.
    is_non_local : bool
        If True, the case is being created on a machine different from the one
        that runs visualCaseGen.
    out : Output
        The output widget to use for displaying log messages.
    """

    cmd = f"./xmlchange {var}={val}"
    if is_non_local is True:
        cmd += " --non-local"

    out = DummyOutput() if out is None else out
    with out:
        print(f"{cmd}\n")

    if not do_exec:
        return

    runout = subprocess.run(cmd, shell=True, capture_output=True, cwd=caseroot)
    if runout.returncode != 0:
        raise RuntimeError(f"Error running {cmd}.")
