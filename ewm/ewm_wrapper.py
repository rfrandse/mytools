#!/usr/bin/env python
"""
Only use this tool if Python3 isn't setup in your environment.  It attempts to find a
valid Python3 interpreter and start ewm.py.
"""
import json
import os
import shlex
import subprocess
import sys

REPO_PATH = os.path.dirname(os.path.realpath(__file__))
EWM_PY_PATH = REPO_PATH + os.sep + "ewm.py"
CONFIG_PATH = REPO_PATH + os.sep + "config"


def run_command(command_string, ignore_error=False, verbose=False, input=None):
    """
    Run shell command and caputure output.

    Args:
        command_string: a shell command to execute
        ignore_error: should an exception be raised if the shell command fails.
        verbose: print the shell command's output

    Returns:
        a tuple with the shell command's return code and output.
        return_code: integer, 0 = success
        output: a list with the trailing new line stripped.
    """
    command_list = shlex.split(command_string)

    # Command's STDERR will be piped to STDOUT, so stderr, should be empty
    command = subprocess.Popen(command_list,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               universal_newlines=True
                               )

    (stdout, stderr) = command.communicate(input)
    returncode = command.returncode

    # Terminate this script if the previous shell command fails.
    if (not ignore_error and (returncode != 0)):
        print("command:     {0}".format(command_list))
        print("return code: {0}".format(returncode))
        print("process pid: {0}".format(command.pid))
        print("output:\n    {0}".format(stdout))
        raise ValueError

    if (verbose):
        print("command:     {0}".format(command_list))
        print("return code: {0}".format(returncode))
        print("process pid: {0}".format(command.pid))
        print("output:\n    {0}".format(stdout))

    # Return a list of the command's output, removing any empty lines.  Python3 returns a bytes
    # object, so need to convert to a string first.
    try:
        command_output = stdout.split("\n")
    except TypeError:
        stdout = stdout.decode("utf-8")
        command_output = stdout.split("\n")

    command_output = [line.rstrip() for line in command_output]

    return (returncode, command_output)


def python3_paths_config():
    """ Load the possible paths that contain a python3 install """
    python3_json_file = CONFIG_PATH + os.sep + "python3_paths.json"

    with open(python3_json_file, "r") as FH:
        python3_paths = json.load(FH)

    return python3_paths


def main():
    """ call ewm.py with a valid python3 interpreter """

    # If a single command line argument contains a space, put quotes around the entire
    # string, so the value gets passed in as a single argument instead of multiple
    # values.
    #
    # Also, check if --verbose arg supplied
    ARGS = []
    verbose = False
    for arg in sys.argv[1:]:
        if ' ' in arg:
            arg = "'" + arg + "'"
        if arg == '--verbose':
            verbose = True
        ARGS.append(arg)

    # Detect running version of python and start the underlying tool with a valid
    # Python3 version
    python3_path = ""
    if (sys.version_info.major < 3):
        if verbose:
            print("Python Version: {}".format(sys.version))
            print("Not running Python3.  Attempting to find a valid install...")
        python3_paths = python3_paths_config()
        for path in python3_paths:
            if (os.path.exists(path)):
                # ENV variable is used by ewm.py tool
                os.environ["PYTHON3_PATH"] = path
                python3_path = path
                break
    else:
        python3_path = sys.executable

    if (not os.path.exists(python3_path)):
        print("Unable to find Python3 Path")
        sys.exit(1)

    # Pass all command line args to the underlying tool
    cmd = " ".join([python3_path, EWM_PY_PATH] + ARGS)
    (rc, output) = run_command(cmd, ignore_error=True)
    if verbose:
        print(cmd)
        print("rc = {}".format(rc))
        print("")

    # Remove blank lines at the end of output
    if output:
        while not output[-1]:
            output.pop()
            # No more output to remove or last line contains text.
            if (not output or output[-1]):
                break

    # Always print command's output
    print("\n".join(output))

    # Set wrapper return code to ewm.py exit status.
    sys.exit(rc)


if __name__ == "__main__":
    main()
