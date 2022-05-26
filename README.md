# mytools

* autobump.py 
```
Local recipe bumping tool. Find bitbake metadata files (recipes) that use the
github.com etc and check the project repository for given revision. Generate
commits that update bitbake metadata files with SRCREV if given revision is
new Generate commit.


```

* ab.py 
```
Derived from autobump.py adds git shortlog list of repository commits to commit message

usage: ab.py [-h] [-d] [-v] [-r REMOTE] [-o ORG] project_name project_sha
REMOTE default = github.com
ORG default = ibm-openbmc


Examples: 
Using defaults
pldm recipe:  SRC_URI = "git://github.com/ibm-openbmc/pldm;nobranch=1"

ab.py pldm  <40 character sha value> 
equivalent command without using defaults.
ab.py -r github.com -o openbmc pldm  <40 character sha value>

Upstream 
phosphor-loggin recipe: SRC_URI += "git://github.com/openbmc/phosphor-logging"
ab.py -o openbmc phosphor-logging <40 character sha value>
or 
ab.py -r github.com -o openbmc phosphor-logging <40 character sha value>

GHE
ab.py -r <ghe url> -o openbmc webui-vue  <40 character sha value>


Uses config.py for 
py_token = ""
py_ibm_token = ""

allowing access to repositories to generate git shortlog list

```
* commitTracker.py

* crn.py
```
Create Release Note (Derived from commitTracker.py)

positional arguments:
  earliest_commit       A reference to the earliest commit to get information
                        for
  latest_commit         A reference (branch name, HEAD, SHA, etc.) to the most
                        recent commit to get information for

  --wiki WIKI           If set to a file path, this script will write an wiki
                        markdown version of the console to the file path given

Example:
 git clone <ibm url>/release-notes.wiki.git

 crn.py fw1020.00-57.9 fw1020.00-57.10 --wiki 1020/fw1020.00-57.10.md


Uses config.py for 
py_token = ""
py_ibm_token = ""
```

* fgh.py 

```
Need to install 
https://cli.github.com/manual/installation
https://github.com/cli/cli
Current version
https://github.com/cli/cli/releases/tag/v2.11.3


Example 
fgh.py is  wrapper around gh
-d option for dry-run

fgh.py -B 1020 -d


gh pr create -R github.ibm.com/openbmc/openbmc -B 1020 -b '#### 1020: meta-ibm: Add hostfw image support (#214)
\`\`\`
Add support for a hostfw image.

Change-Id: I1b4be263b0eb44c324db4f41ea563fdf2a8ad8b5
Signed-off-by: Adriana Kobylak <anoo@us.ibm.com>\`\`\`' -t '1020: meta-ibm: Add hostfw image support (#214)'

```
* del-branch.py
```
Useful to delete branches in a bulk
Its a cut and paste program because I want to be carefull what is deleted. 
I have my github.ibm.com/openbmc/openbmc set to delete branch after merging. 

The program grabs everything at the end of a line after the back-slash

git fetch --all -p
Fetching mypr
From github.ibm.com:rfrandse/openbmc
 - [deleted]               (none)     -> mypr/1020g-bmcweb
 - [deleted]               (none)     -> mypr/1020g-fan
 - [deleted]               (none)     -> mypr/1020g-pldm
 - [deleted]               (none)     -> mypr/1020g-power


running tool here is what it looks like, Carriage return after list then ctrl-d

del-branch.py 
Enter/Paste your list of branches to delete. ctrl-d to execute .
 - [deleted]               (none)     -> mypr/1020g-bmcweb
 - [deleted]               (none)     -> mypr/1020g-fan
 - [deleted]               (none)     -> mypr/1020g-pldm
 - [deleted]               (none)     -> mypr/1020g-power


['-D', '1020g-bmcweb', '1020g-fan', '1020g-pldm', '1020g-power']
Deleted branch 1020g-bmcweb (was 674ccde0c9).
Deleted branch 1020g-fan (was a4fec3a905).
Deleted branch 1020g-pldm (was b495325a23).
Deleted branch 1020g-power (was 3abaaef021).
```
