#!/usr/bin/env python3
#
# Not all CMC RHEL7 machines have the requests module installed under the rh-python36
# software collection. gfwr610 for example does.
#
# --- We will have to get this resolved via Hai so this module exists on out pool
# machines.
#
# re error:  ModuleNotFoundError: No module named 'requests'
# To install, you should be able to do something like this (assuming you can write
# there)
#  source /opt/rh/rh-python36/enable
#  pip install requests
#
# pip will create this /opt/rh/rh-python36/root/usr/lib/python3.6/site-packages/requests
#  as well as some other stuff like urllib3
#
# 06/25/21 joshande created
#

import json
import os
import sys

# Create the EWM object
# Note: tools located outside /esw/bin/bld will need to setup their environment to
# make sure they can find the ewm.py module.
sys.path.append("/esw/bin/bld")
import ewm
instance = ewm.Ewm()

print("Running whoami")
print(instance.whoami())


markerQueryName = "FSP marker lid EWM ids"
print("\nRunning query: {}".format(markerQueryName))
query = instance.runquery(markerQueryName)

count = 0;
maxtoshow = 2;

print("----------------- Output from running a query and processing the result:")
for element in query['results']:
    print("\nid:       ", element["Id"]);
    print("  summary:  ", element["Summary"]);
    print("  modified: ", element["Modified Date"]);
    print("  status:   ", element["Status"]);
    print("  owner:    ", element["Owned By"]);
    print("  priority: ", element["Priority"]);

    count += 1
    if (count > maxtoshow):
        print("")
        break

print("----------- Use the 'display' and work with the result")

# should be able to use an int or string type
ewmId = "284526"
workItem = instance.display(ewmId)

print("\nId : ", workItem["Universal ID"])
print("    Universal ID           : ", workItem["Universal ID"])
print("    Summary                : ", workItem["Summary"])
print("    Severity               : ", workItem["Severity"])
print("    State                  : ", workItem["State"])
print("    Status                 : ", workItem["Status"])
print("    Tags                   : ", workItem["Tags"])
print("    Priority               : ", workItem["Priority"])
print("    Priority Justification : ", workItem["Priority Justification"])

