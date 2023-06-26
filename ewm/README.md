# ewm
Tool to interact with EWM/RTC

# Quick Start
```bash
# Clone repository      
git clone --recurse-submodules git@github.ibm.com:power-devops/ewm.git

# Add a new login line to $HOME/.netrc
machine EWM login W3ID password W3PASSWORD

# Setup Python3.6 on RHEL (optional)
source /opt/rh/rh-python36/enable

# Test authentication (use ewm_wrapper.py if Python3.6+ isn't setup in your environment)
./ewm/ewm.py whoami
./ewm/ewm_wrapper.py whoami

# Run a query
./ewm/ewm.py runquery "Active STG Defects I Am Subscribed To"

# View a Work Item
./ewm/ewm.py display 276281

# Print rtcwi.py main help message
./ewm/ewm.py help

# Print rtcwi.py subcommand help message
./ewm/ewm.py help display

# Print ewm.py action/subcommand help
./ewm/ewm.py view --help
```

# EWM.py specific enhancements (not directly used by rtcwi.py)
```bash
# Filter output based on Work Item Attribute (quote attribute with spaces)
ewm.py view --id 276281 --attribute Summary
Code Update Signing from Signing Server

# Convert JSON query output to text
ewm.py runquery "Active STG Defects I Am Subscribed To" --text-mode
Type|Universal ID|Id|Summary|Owned By|Status|Priority|Severity|Modified Date
STG Defect|PE009H6M|282739|test - feature type|fspbld@us.ibm.com|Open|Unassigned|4 - Minimal|2021-06-09T10:32:57.998000
STG Defect|SW522645|276281|Code Update Signing from Signing Server|eggler@us.ibm.com|Working|Unassigned|3 - Moderate|2021-06-08T17:08:14.726000
```

# Module import error "requests"
If you see this error, that means the Python module "requests" isn't installed for 
your python distribution.  I believe Hai Phan has this installed on all the managed CMC 
machines like gfwr610.rchland.ibm.com.  However, this wasn't installed by default on the 
BMC build machines.  I can add this module to this repo in the future, but at the moment, 
you can install that to your system with `pip install requests`.
