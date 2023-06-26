#!/usr/bin/env python3
"""
Command line tool and importable Python3 module used to interact with EWM issue tracking
tool.
"""
import argparse
import configparser
import json
import netrc
import os
import re
import shlex
import subprocess
import sys

# Establish the paths to different directories within the repository
REPO_PATH = os.path.dirname(os.path.realpath(__file__))
LIB_PATH = REPO_PATH + os.sep + "lib"
sys.path.append(LIB_PATH)
CONFIG_PATH = REPO_PATH + os.sep + "config"

# The release path has a variable release directory name.
RTCWI_PATH = REPO_PATH + os.sep + "rtcwi-cli"
RTCWI_DIRECTORIES = os.listdir(RTCWI_PATH)
RTCWI_RELEASE = "rtcwi-21.1.2"
for directory in RTCWI_DIRECTORIES:
    match = re.search(r"^(rtcwi-\d.*)", directory)
    if (match):
        RTCWI_RELEASE = match.group(0)
        break
RTCWI_RELEASE_PATH = RTCWI_PATH + os.sep + RTCWI_RELEASE
RTCWI_SCRIPTS_PATH = RTCWI_RELEASE_PATH + os.sep + "scripts"

# Custom Python Modules
import issuetracker

# rtcwi.py needs a python3 interpreter to run.  If the exported environment's PATH
# doesn't use a python3 binary named "python", the shebang "#!/usr/bin/env python"
# might use a python2 binary.  Therefore, use the current running interpreter to call
# rtcwi.py unless there is an explicitly set environment variable.
#
# Note: This script's shebang explicitly calls for python3, so it can be used to start
# rtcwi.py
PYTHON3_PATH = sys.executable
# if "PYTHON3_PATH" in os.environ:
#     print("PYTHON3_PATH: {}".format(os.environ["PYTHON3_PATH"]))
#     PYTHON3_PATH = os.environ["PYTHON3_PATH"]


class Ewm(issuetracker.IssueTracker):
    """
    Interact with an EWM/RTC tool instance to create, view, and update Work Items.  This
    class relies on using an underlying rtcwi.py tool developed by the System DevOps
    team; however, it abstracts away some of the complexities of working with the tool
    like authentication, project, and repository settings.

    There are various ways to provide authentication information, but the recommended way
    is to rely on the tool's default settings and provide login credentials via your
    $HOME/.netrc file.  Make sure this file has the appropriate permissions since your
    password is stored in clear text.  Eg: chmod 660 $HOME/.netrc

    Add the following line to your $HOME/.netrc file to provide login credentials:
    machine EWM login W3EMAIL password W3PASSWORD

    This class supports 4 generic methods or "actions" for issue tracking tools as well
    as maps the rtcwi.py subcommands to a matching method name (replacing dashes with
    an underscore).
    Generic Methods:
    1. addnote
    2. create
    3. modify
    4. view

    Methods:
        # Generic issue tracking methods
        addnote: add a note to a Work Item
        create: create a new Work Item
        modify: update a detail in a Work Item
        view: get the contents of a Work Item

        # Remaining rtcwi.py subcommands
        login: authenticate to the tool from the established credentials
        help: print help information for the various rtcwi.py commands
        display: get the contents of a Work Item
        whoami: print the currently authenticated user
        CLEAR: remove rtcwi.py configuration files
        setcwe: store default credentials for the current working environment
        listqueries: list the queries available in the current project area
        runquery: run a specified query
        subscribe: allow a user to be notified of Work Item updates
        unsubscribe: remove a user from Work Item updates
        link: add a link to a Work Item
        unlink: remove a link to a Work Item
        addcomment: add a note to a Work Item
        list: print various details about the rtcwi.py CLI environment or project area.
        browser: open a specified work item or URL in a web browser.
        search: run a full text search for work items in an EWM Project.
        logout: logs the user out of a repository.
        swat_catowners: Use SWAT Servicelayer REST APIs to display an RTC project's
                        categories and those category's owners
    """

    def __init__(self, config_file=""):
        """
        Establish authentication credentials and setup rtcwi.py dependencies.

        Args:
            config_file: a path to an .ini file containing configuration information.

        Returns:
            An Ewm object
        """

        self.authenticated = False
        self.basecmd = ""
        # The command line option string for both the project and repository
        self.cli_opts = ""
        # The clear text w3 password.  Do not print this value.
        self.password = ""
        self.project = ""
        self.repository = ""
        self.username = ""

        self._setup_config(config_file)
        self._setup_rtcwi()

    def addnote(self, id, message):
        """
        Add a note/comment to the specified work item.

        Args:
            id: string for the work item ID
            message: the message to add to the work item

        Returns:
            bool: indicating if a note was successfully added
        """

        self._login()

        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "addcomment",
                        "{}".format(id),
                        "'{}'".format(message)])

        (rc, output) = run_command(cmd)
        return rc == 0

    def create(self, witype="", attributes=[], wifile="", original_syntax=""):
        """
        Create a new work item.

        Args:
            id: string for the work item ID,
            witype: string for the new type of work item to create.
                types found in: ewm.py list types
                Eg: "STG Defect", "Story", "Task",
            attributes: list of strings for KEY:VALUE attributes to create.  These have a
                higher priority than attributes specified in wifile.  This implementation is
                kind of messy, so passing in the JSON wifile is preferred.

                The KEY needs to end with a ':' or the ':', needs to be passed as the next item
                in the list.  The "," is optional after VALUE is only 1 KEY:VALUE is used.
                If multiple KEY:VALUE are used, the "," needs to be the next character after VALUE
                or the next item in the list.
                Eg: ["Description:", "my new description",
                     ",", "Tags:", "foo bar",
                     ",", "System Name:", "Code Name"]
            wifile: string for the JSON file containing the attributes to create.  These
                have a lower priority the the 'attributes' parameter.
            original_syntax: string to be directly used by rtcwi.py.  Do not use this with
                other parameters.
                Eg: '"STG Defect" --wifile ./my_new_defect.json'

        Returns:
            data: the JSON representing the newly created work item

        Example command line:
        ewm.py create --type "STG Defect" \
                      --wifile ./config/workitem_template.json \
                      --attributes "Owned By": joshua.andersen1@ibm.com
        """
        self._login()

        if original_syntax:
            cmd = " ".join([self.basecmd, self.cli_opts, "create", original_syntax])
        else:
            cmd_wifile = "--wifile " + wifile if wifile else ""

            witype = "'" + witype + "'"

            # Need to reapply quotes around attributes KEY or VALUE that have a space in them.
            # Just do everything to simplify logic.
            for i, attribute in enumerate(attributes):
                attributes[i] = "".join(["'", attributes[i], "'"])

            cmd = " ".join([self.basecmd,
                            self.cli_opts,
                            cmd_wifile,
                            "create",
                            witype] + attributes)

        (rc, output) = run_command(cmd)
        data = json.loads("".join(output))
        return data

    def modify(self, id="", state="", attributes=[], wifile="", original_syntax=""):
        """
        Modify contents of a work item.

        Args:
            id: string for the work item ID,
            state: string for the newly desired state. Depending on the state,
                additional attributes might also be needed.
                Eg: Open, More Info, Close
            attributes: list of strings for KEY:VALUE attributes to modify.  These have a
                higher priority than attributes specified in wifile.  This implementation is
                kind of messy, so passing in the JSON wifile is preferred.

                The KEY needs to end with a ':' or the ':', needs to be passed as the next item
                in the list.  The "," is optional after VALUE is only 1 KEY:VALUE is used.
                If multiple KEY:VALUE are used, the "," needs to be the next character after VALUE
                or the next item in the list.
                Eg: ["Description:", "my new description",
                     ",", "Tags:", "foo bar",
                     ",", "System Name:", "Code Name"]
            wifile: string for the JSON file containing the attributes to modify.  These
                have a lower priority the the 'attributes' parameter.
            original_syntax: string to be directly used by rtcwi.py.  Do not use this with
                other parameters.
                Eg: '21333 Summary: "new summary from command line"'

        Returns:
            data: the JSON representing the modified work item
        """

        self._login()

        if original_syntax:
            cmd = " ".join([self.basecmd, self.cli_opts, "modify", original_syntax])
        else:
            cmd_wifile = "--wifile " + wifile if wifile else ""
            cmd_state = "--action '" + state + "'" if state else ""

            # Need to reapply quotes around attributes KEY or VALUE that have a space in them.
            # Just do everything to simplify logic.
            for i, attribute in enumerate(attributes):
                attributes[i] = "".join(["'", attributes[i], "'"])

            cmd = " ".join([self.basecmd,
                            self.cli_opts,
                            "modify",
                            id,
                            cmd_wifile,
                            cmd_state] + attributes)

        (rc, output) = run_command(cmd)
        data = json.loads("".join(output))
        return data

    def view(self, id, attribute="", text=False):
        """
        Get contents of a work item

        Args:
            id: string for the work item ID
            attribute: filter result based on this key
            text: return the item in text mode versus the default json

        Returns:
            data: the json/text representing a work item
        """

        self._login()
        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "display",
                        "{}".format(id)])

        (rc, output) = run_command(cmd)
        json_string = "".join(output)
        data = json.loads(json_string)

        if attribute and attribute in data:
            return data[attribute]

        return data

    def login(self, username="", password="", repository="", project=""):
        """  Login to the underlying rtcwi.py tool """

        if username:
            self.username = username
        if password:
            self.password = password
        if repository:
            self.repository = repository
        if project:
            self.project = project

        self._login()

    def help(self, subcommand=""):
        """
        Get the help messages for the rtcwi.py subcommands

        Args:
            subcommand: optional subcommand to display specific help messaging
                        eg: display, whoami, or runquery

        Returns:
            output: the help message contents
        """

        self._login()
        cmd = self.basecmd + " help " + subcommand

        (rc, output) = run_command(cmd)
        # Remove trailing newlines
        while not output[-1]:
            output.pop()
        return output

    def display(self, id):
        """
        Get contents of a work item

        Args:
            id: string for the work item ID

        Returns:
            data: the json/text representing a work item
        """

        self._login()
        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "display",
                        "{}".format(id)])

        (rc, output) = run_command(cmd)
        json_string = "".join(output)
        data = json.loads(json_string)

        return data

    def whoami(self):
        """
        Determine the authenticated user.

        Returns:
            whoami: string of the authenticated user
        """

        self._login()
        cmd = " ".join([self.basecmd, self.cli_opts, "whoami"])
        (rc, output) = run_command(cmd)

        return output[0]

    def CLEAR(self):
        """
        Remove any saved current working environment from the filesystem.
        Most likely saved in $HOME/.rtcwicli

        Returns:
            nothing or a list of empty strings.
        """

        self._login()

        cmd = " ".join([self.basecmd, self.cli_opts, "CLEAR"])

        (rc, output) = run_command(cmd)
        return output

    def setcwe(self, repository="", project="", user=""):
        """
        Save the current working environment.  Most likely save in $HOME/.rtcwicli.
        Default current working environment created on object construction, but
        explicit overrides can be passed via this method's args.

        Args:
            repository: string of the EWM URL to connect
            project: string of the EWM Project
            user: W3 ID (email) that is used to login

        Returns:
            list of the recently created working environment
        """
        self._login()

        repo = repository
        proj = project
        username = user

        # Use object's default values if not explicitly passed in.
        if (not repo):
            repo = self.repository
        if (not proj):
            proj = self.project
        if (not username):
            username = self.username

        cmd = " ".join([self.basecmd,
                        "setcwe",
                        "-r {}".format(repo),
                        "-p {}".format(proj),
                        "-u {}".format(username)])

        (rc, output) = run_command(cmd)
        return output

    def listqueries(self):
        """
        List the queries available in the current project area.

        Returns:
            JSON formatted list of queries.  Query dictionary element contains
            "Description" and "Name" keywords.
        """
        self._login()

        cmd = " ".join([self.basecmd,
                        "listqueries",
                        self.cli_opts])

        (rc, output) = run_command(cmd)
        data = json.loads("".join(output))
        return data

    def runquery(self, query_name, text_mode=False):
        """
        Run the specified query.  If text_mode=True, return a list of matches.  The
        first element in the list will be the separated keywords, and all subsequent
        lines will be the results of the query.

        text mode example:
        Type|Universal ID|Id|Summary|Owned By|Status|Priority|Severity|Modified Date
        STG Defect|SW522645|276281|Code Update Signing from Signing Server|...

        Args:
            query_name: string of query to run
            text_mode: bool.  True forces '|' separated query results (one per line).

        Returns:
            Either a JSON dictionary (True) or list (False) of '|' results (one per
            line) depending on the value of text_mode.
        """

        self._login()

        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "runquery",
                        "'{}'".format(query_name)])

        (rc, output) = run_command(cmd)
        data = json.loads("".join(output))

        # The normal JSON dictionary
        if not text_mode:
            return data

        # Create a "|" separated header's line with each additional line containing
        # a single match from the query.
        text = []
        headers = data["headers"]
        text.append("|".join(headers))

        for result in data["results"]:
            result_list = []
            for header in headers:
                result_list.append(result[header])
            text.append("|".join(result_list))
        return text

    def subscribe(self, id, userid):
        """
        Add the W3 ID (email) to the list of subscribers for the work item.  Any valid
        W3 can be subscribed

        Args:
            id: string for the work item ID to subscribe the userid
            userid: a list of W3 IDs.

        Returns:
            A list of subscribed user IDs.
        """

        self._login()

        userid_string = " ".join(userid)

        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "subscribe",
                        id,
                        userid_string])

        (rc, output) = run_command(cmd)
        current_subscribers = json.loads("".join(output))
        return current_subscribers

    def unsubscribe(self, id, userid=""):
        """
        Remove the W3 ID (email) from the list of subscribers for the work item.  Only
        your userid can be unsubscribed.  Defaults to the logged in user.

        Args:
            id: string for the work item ID to subscribe the userid
            userid: The W3 ID to unsubscribe (case sensitive).

        Returns:
            A list of subscribed user IDs.
        """

        self._login()

        # The userid to unsubscribe is case sensitive whereas the login userid is not.
        # So, this default value might not explicitly work.
        if (not userid):
            userid = self.username

        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "unsubscribe",
                        id,
                        userid])

        (rc, output) = run_command(cmd)
        current_subscribers = json.loads("".join(output))
        return current_subscribers

    def link(self, id, link_type, work_item_ids):
        """
        Add a link to a work item.  To determine a valid link_type:
        1. list types -> returns types of work items.  select one of these.
        2. list attributes "selected work item type" -> link_type is any one
               of these values that uses "(link)" next to the attribute.
               Eg: Related Artifacts (link) -> remove the " (link)" string when
               passing in the argument

        Example:
        instance.link("282739", "Related Artifacts", ["http://my_new_link.com"])

        Args:
            id: string for the work item ID to subscribe the userid
            link_type: string for the type of link to add.
            work_item_ids: a list of work item ids or the appropriate info for the
                           selected link type.

        Returns:
            a string "Link added"
        """
        self._login()

        link_type = "'" + link_type + "'"
        work_item_ids_string = " ".join(work_item_ids)

        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "link",
                        id,
                        link_type,
                        work_item_ids_string])

        (rc, output) = run_command(cmd)
        return output

    def unlink(self, id, link_type, work_item_ids):
        """
        Remove a link from a work item. See "link" method for more details.

        Args:
            id: string for the work item ID to subscribe the userid
            link_type: string for the type of link to add.
            work_item_ids: a list of work item ids or the appropriate info for the
                           selected link type.

        Returns:
            a string "Link removed".  Doesn't throw error if unsuccessful
        """
        self._login()

        link_type = "'" + link_type + "'"
        work_item_ids_string = " ".join(work_item_ids)
        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "unlink",
                        id,
                        link_type,
                        work_item_ids_string])

        (rc, output) = run_command(cmd)
        return output

    def addcomment(self, id, comment):
        """
        Add a note/comment to the specified work item.

        Args:
            id: string for the work item ID
            message: the message to add to the work item

        Returns:
            bool: indicating if a note was successfully added
        """

        self._login()

        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "addcomment",
                        "{}".format(id),
                        "'{}'".format(comment)])

        (rc, output) = run_command(cmd)
        return rc == 0

    def list(self, topic="", qualifiers=""):
        """
        List information about the EWM CLI environment or project area.  See
        "ewm.py help list" for more information.

        Examples:
            ewm.py list cwe
            ewm.py list attributes "STG Defect"

        Args:
            topic: string of topic to list information about.
            qualifiers: optional string of additional information about what to list.

        Returns:
            list: output from a given topic and qualifiers
        """
        self._login()

        # Quote strings in case there are spaces in the variable.
        topic = "'" + topic + "'"
        qualifiers = "'" + qualifiers + "'"

        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "list",
                        topic,
                        qualifiers])
        (rc, output) = run_command(cmd)
        return output

    def browser(self):
        self._login()
        print("NOT IMPLEMENTED")

    def search(self, search_text, max_num=""):
        """
        Runs a full text search for work items in an EWM Project.  A simple string
        can be given as the argument and it will return the resulting work items
        in json format.

        Args:
            search_text: text input from user to search
            max_num: int for maximum number of work items returned.

        Returns:
            JSON formatted results
        """

        self._login()

        search_text = "'" + search_text + "'"

        max_text = ""
        if max_num:
            max_text = "--max {}".format(max_num)

        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "search",
                        search_text,
                        max_text])

        (rc, output) = run_command(cmd)

        return json.loads("".join(output))

    def logout(self):
        """ logout of the current session. """
        cmd = " ".join([self.basecmd, self.cli_opts, "logout"])

        (rc, output) = run_command(cmd)
        self.authenticated = False

    def swat_catowners(self):
        self._login()
        print("NOT IMPLEMENTED")

    # Private Methods
    def _login(self):
        """ Only login once per session """

        if (self.authenticated):
            return

        cmd = " ".join([self.basecmd,
                        self.cli_opts,
                        "login",
                        "-u {}".format(self.username)])

        (rc, output) = run_command(cmd, input=self.password)
        self.authenticated = True

    def _setup_config(self, config_file):
        """
        Setup the 4 authentication parameters
        1. username
        2. password
        3. repository
        4. project
        """

        # 1. Establish tool specific defaults
        default_ewm_file = CONFIG_PATH + os.sep + "default_ewm.ini"
        if (os.path.exists(default_ewm_file)):
            self._parse_config_ini(default_ewm_file)

        # 2. Establish Default Username
        if "USER" in os.environ:
            self.username = os.environ["USER"] + "@us.ibm.com"

        # 3. Parse .netrc line-> EWM login MYUSERNAME password MYPASSWORD
        home_netrc_file = ""
        if "HOME" in os.environ:
            home_netrc_file = os.environ["HOME"] + os.sep + ".netrc"
        if (os.path.exists(home_netrc_file)):
            my_netrc = netrc.netrc(home_netrc_file)
            if "EWM" in my_netrc.hosts:
                (login, account, password) = my_netrc.authenticators("EWM")
                self.username = login
                self.password = password

        # 4. Parse Custom Config
        if (os.path.exists(config_file)):
            self._parse_config_ini(config_file)

        # 5. Parse Environmental Variables
        if "EWM_ID" in os.environ:
            self.username = os.environ["EWM_ID"]
        if "EWM_PASSWORD" in os.environ:
            self.password = os.environ["EWM_PASSWORD"]
        if "EWM_PROJECT" in os.environ:
            self.project = os.environ["EWM_PROJECT"]
        if "EWM_REPOSITORY" in os.environ:
            self.repository = os.environ["EWM_REPOSITORY"]

        # The project could have spaces in the name, so quote it to make sure it is
        # passed on the command line as a single argument.
        self.project = "'" + self.project + "'"

        # After the settings are parsed, construct the string that is included
        # in every rtcwi.py command.
        self.cli_opts = " -p {} -r {}".format(self.project, self.repository)

    def _parse_config_ini(self, file_path):
        """ Read a .ini file, and return the 4 project details """
        # File containing a password
        authentication_file = ""
        password = ""

        config_parser = configparser.ConfigParser()
        FH = open(file_path, "r")
        config_parser.read_file(FH)
        FH.close()

        if "ewm" in config_parser:
            if "id" in config_parser["ewm"]:
                self.username = config_parser["ewm"]["id"]
            if "password" in config_parser["ewm"]:
                password = config_parser["ewm"]["password"]
            if "project" in config_parser["ewm"]:
                self.project = config_parser["ewm"]["project"]
            if "repository" in config_parser["ewm"]:
                self.repository = config_parser["ewm"]["repository"]
            if "authentication_file" in config_parser["ewm"]:
                authentication_file = config_parser["ewm"]["authentication_file"]
                authentication_file = authentication_file.replace("$HOME",
                                                                  os.environ["HOME"])

        if (not password and os.path.exists(authentication_file)):
            FH = open(authentication_file)
            password = FH.readline().strip()
            FH.close()
            self.password = password

        return

    def _setup_rtcwi(self):
        """ Add the Paths to import rtcwi.py """

        self.basecmd = PYTHON3_PATH + " " + RTCWI_SCRIPTS_PATH + os.sep + "rtcwi.py "

        # Allow python to find the rtcwi.py specific packages.
        if "PYTHONPATH" not in os.environ:
            os.environ["PYTHONPATH"] = RTCWI_RELEASE_PATH
        else:
            os.environ["PYTHONPATH"] = RTCWI_RELEASE_PATH + os.pathsep + os.environ["PYTHONPATH"]


# Miscellaneous Functions
def run_command(command_string, ignore_error=False, verbose=False, input=None):
    r"""
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

    # Hack to make Window's commands work. shlex.split works in POSIX mode by default,
    # so convert path's containing a backslash to a forward slash.  This is also able
    # to handle single quote quoting (which isn't possible in Window's CMD).
    if (os.sep == "\\"):
        command_string = command_string.replace("\\", "/")

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
        raise ValueError("Nonzero Return Code")

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


def parse_command_line():
    """ """
    # Setup Command Line Parser.
    # The main/top parser.
    parser = argparse.ArgumentParser(
        description="%(prog)s interacts with EWM using the underlying rtcwi.py tool."
                    " The second argument is an action for the tool to take which."
                    " Could be a generic action or one of the available subcommands"
                    " for rtcwi.py.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=False,
        prefix_chars="-+")

    # Top level options
    ewm_options = parser.add_argument_group(title="EWM-OPTIONS",
                                            description="Top Level Options")
    ewm_options.add_argument(
        "--ewm-config",
        default="",
        help="Config file for program.  Explicit override for default vaules."
    )

    ewm_options.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra information about the script."
    )

    ewm_options.add_argument("--outfile", help="File to store rtcwi.py output")

    ewm_options.add_argument(
        "-h", "--help", action="help", help="show this help message and exit"
    )

    # Create subcommands.  The 'dest' value maps the subparser used to action
    subparsers = parser.add_subparsers(help="The 'ACTION' to take", dest="action")

    # The 4 generic actions
    # 1. addnote subcommand
    parser_addnote = subparsers.add_parser("addnote",
                                           help="add a note/comment to a Work Item")
    parser_addnote.add_argument("--id", type=str, help="Work Item ID")
    parser_addnote.add_argument("--message", type=str, help="Message to add.")

    # 2. create subcommand (overlap with rtcwi.py subcommand)
    parser_create = subparsers.add_parser("create",
                                          help="create a new Work Item")
    parser_create_choose = parser_create.add_mutually_exclusive_group(required=True)
    parser_create_choose.add_argument("--original-syntax",
                                      type=str,
                                      help="Argument formatted exactly like a call to the"
                                      " original tool would look.  If using this option,"
                                      " do NOT use any of the other options for this subcommand.")

    parser_create_choose.add_argument("--type",
                                      type=str,
                                      dest="witype",
                                      help="Type of Work Item to create."
                                           " Eg: 'STG Defect'")
    parser_create.add_argument("--attributes",
                               nargs="+",
                               default=[],
                               help="KEY:VALUE comma separated strings for work item"
                               " attributes to modify.  If the KEY or VALUE contains spaces,"
                               " then it needs to be quoted.  Command line"
                               " options override matching values from wifile.")
    parser_create.add_argument("--wifile",
                               type=str,
                               help="JSON formatted file containing the work item"
                               " attributes to create.  This option is preferred over"
                               " --attributes option.")

    # 3. modify subcommand (overlap with rtcwi.py subcommand)
    parser_modify = subparsers.add_parser("modify",
                                          help="update a detail in a Work Item")
    parser_modify_choose = parser_modify.add_mutually_exclusive_group(required=True)
    parser_modify_choose.add_argument("--id", type=str, help="Work Item ID")
    parser_modify_choose.add_argument("--original-syntax",
                                      type=str,
                                      help="Argument formatted exactly like a call to the"
                                      " original tool would look.  If using this option,"
                                      " do NOT use any of the other options for this subcommand.")

    parser_modify.add_argument("--state", type=str, help="new state of the work item")
    parser_modify.add_argument("--attributes",
                               nargs="+",
                               default=[],
                               help="KEY:VALUE comma separated strings for work item"
                               " attributes to modify.  If the KEY or VALUE contains spaces,"
                               " then it needs to be quoted.  Command line"
                               " options override matching values from wifile.")
    parser_modify.add_argument("--wifile",
                               type=str,
                               help="JSON formatted file containing the work item"
                               " attributes to modify.  This option is preferred over"
                               " --attributes option.")

    # 4. view subcommand
    parser_view = subparsers.add_parser("view",
                                        help="get the contents of a Work Item")
    parser_view.add_argument("--id", type=str, help="id description")
    parser_view.add_argument("--attribute",
                             default="",
                             type=str,
                             help="Single attribute to view")

    # The rtcwi.py remaining subcommands
    # 1. login subcommand
    parser_login = subparsers.add_parser("login",
                                         help="authenticate to the tool from the established credentials")

    # 2. help subcommand
    parser_help = subparsers.add_parser("help",
                                        help="print help information for the various rtcwi.py commands")
    parser_help.add_argument("subcommand",
                             type=str,
                             nargs="?",
                             default="",
                             help="the rtcwi.py subcommand to get more details")

    # 3. create subcommand handled above

    # 4. display subcommand
    parser_display = subparsers.add_parser("display",
                                           help="get the contents of a Work Item")
    parser_display.add_argument("id",
                                type=str,
                                help="work item ID to display")

    # 5. modify subcommand handled above

    # 6. whoami subcommand
    parser_whoami = subparsers.add_parser("whoami",
                                          help="print the currently authenticated user")

    # 7. CLEAR subcommand
    parser_CLEAR = subparsers.add_parser("CLEAR",
                                         help="remove rtcwi.py configuration files")

    # 8. setcwe subcommand
    help_setcwe = "store credentials for the current working environment"
    parser_setcwe = subparsers.add_parser("setcwe",
                                          help=help_setcwe)
    parser_setcwe.add_argument("--repository",
                               type=str,
                               help="")
    parser_setcwe.add_argument("--project",
                               type=str,
                               help="")
    parser_setcwe.add_argument("--user",
                               type=str,
                               help="")

    # 9. listqueries subcommand
    parser_listqueries = subparsers.add_parser("listqueries",
                                               help="list the queries available in the current project area")

    # 10. runquery subcommand
    parser_runquery = subparsers.add_parser("runquery",
                                            help="run a specified query")
    parser_runquery.add_argument("query_name",
                                 type=str,
                                 help="Name of the query to run.")
    parser_runquery.add_argument("--text-mode",
                                 action="store_true",
                                 help="Output '|' separated text results instead of"
                                 " JSON formatted.")

    # 11. subscribe subcommand
    parser_subscribe = subparsers.add_parser("subscribe",
                                             help="allow a user to be notified of Work Item updates")
    parser_subscribe.add_argument("id",
                                  type=str,
                                  help="Work Item ID")
    parser_subscribe.add_argument("userid",
                                  nargs="+",
                                  type=str,
                                  help="Space separated list of W3 IDs to add.")

    # 12. unsubscribe subcommand
    parser_unsubscribe = subparsers.add_parser("unsubscribe",
                                               help="remove a user from Work Item updates")
    parser_unsubscribe.add_argument("id",
                                    type=str,
                                    help="Work Item ID")
    parser_unsubscribe.add_argument("userid",
                                    nargs="?",
                                    type=str,
                                    help="W3 ID to unsubscribe.  Only you.")

    # 13. link subcommand
    parser_link = subparsers.add_parser("link",
                                        help="add a link to a Work Item")
    parser_link.add_argument("id",
                             type=str,
                             help="Work Item ID")
    parser_link.add_argument("link_type",
                             type=str,
                             default="",
                             help="Type of the link to add or remove")
    parser_link.add_argument("work_item_ids",
                             type=str,
                             nargs="*",
                             help="Space separated list of work item ids.")

    # 14. unlink subcommand
    parser_unlink = subparsers.add_parser("unlink",
                                          help="remove a link to a Work Item")
    parser_unlink.add_argument("id",
                               type=str,
                               help="Work Item ID")
    parser_unlink.add_argument("link_type",
                               type=str,
                               default="",
                               help="Type of the link to add or remove")
    parser_unlink.add_argument("work_item_ids",
                               type=str,
                               nargs="*",
                               help="Space separated list of work item ids.")

    # 15. addcomment subcommand (synonym for addnote)
    parser_addcomment = subparsers.add_parser("addcomment",
                                              help="add a note/comment to a Work Item")
    parser_addcomment.add_argument("id", type=str, help="Work Item ID")
    parser_addcomment.add_argument("comment", type=str, help="Comment to add.")

    # 16. list subcommand
    parser_list = subparsers.add_parser("list",
                                        help="List information about the RTC CLI environment or project area")
    parser_list.add_argument("topic",
                             type=str,
                             default="",
                             help="Topic to list information about.")
    parser_list.add_argument("qualifiers",
                             type=str,
                             nargs="?",
                             default="",
                             help="Additional information about what to list.")

    # 17. browser subcommand
    parser_browser = subparsers.add_parser("browser",
                                           help="open a specified work item or URL in a web browser.")

    # 18. search subcommand
    parser_search = subparsers.add_parser("search",
                                          help="run a full text search for work items in an EWM Project.")
    parser_search.add_argument("search_text", type=str, help="text input from user to search")
    # max is a Python builtin function, so store the value in a different variable
    # name to fix any name collisions.
    parser_search.add_argument("-m", "--max",
                               dest="max_num",
                               type=int,
                               help="the max number of work items returned")

    # 19. logout subcommand
    parser_logout = subparsers.add_parser("logout",
                                          help="logs the user out of a repository.")

    # 20. swat-catowners subcommand
    help_swat_catowners = "Use SWAT Servicelayer REST APIs to display an RTC project's" \
                          " categories and those category's owners"
    parser_swat_catowners = subparsers.add_parser("swat-catowners",
                                                  help=help_swat_catowners)

    # Separate the options into two dictionaries consisting of the main command's
    # options and the subcommands
    options_main_keys = {"ewm_config", "verbose", "outfile", "action"}

    options_all = parser.parse_args()

    options_main = {key: value for key, value in vars(options_all).items()
                    if key in options_main_keys}
    options_subcommand = {key: value for key, value in vars(options_all).items()
                          if key not in options_main_keys}

    if options_all.verbose:
        print(options_main)
        print(options_subcommand)

    return options_main, options_subcommand


def main():
    """
    Parse the command line and transform the arguments into the appropriate
    EWM method call.
    """

    options, kwargs = parse_command_line()

    instance = Ewm(options["ewm_config"])

    # Translate the action/subcommand value into the appropriate method call
    try:
        action = getattr(instance, options["action"])
    except AttributeError:
        print("I don't recognize your requested action: {}".format(options["action"]))
        sys.exit(1)

    args = []

    # Perform the desired action
    try:
        value = action(*args, **kwargs)
    except TypeError as e:
        print("Action '{}' doesn't have the correct arguments".format(options["action"]))
        print(e.args)
        sys.exit(1)

    # Print the results
    if type(value) is dict:
        print(json.dumps(value, sort_keys=True, indent=4))
    elif type(value) is list:
        try:
            print("\n".join(value))
        # Some kind of nested list data structure occurred.
        except TypeError:
            print(json.dumps(value, sort_keys=True, indent=4))
    elif type(value) is str:
        print(value)

    # Save results to a file.
    if (options["outfile"]):
        print("Writing: {}".format(options["outfile"]))
        with open(options["outfile"], "w") as FH:
            if type(value) is dict:
                json.dump(value, FH, sort_keys=True, indent=4)
            elif type(value) is list:
                for item in value:
                    FH.write(item + "\n")
            elif type(value) is str:
                FH.write(value)


if __name__ == "__main__":
    main()
