#!/usr/bin/python2
print "Enter/Paste your list of branches to delete. ctrl-d to execute ."

import re
import subprocess
PIPE = subprocess.PIPE

contents = []
branch_list = ['-D']

def git_branch(parms_array):

    git_args = ['git', 'branch']+parms_array

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()

          
    return stdoutput


contents = []
while True:
    try:
        line = raw_input("")
    except EOFError:
        break
    contents.append(line)

data = ""
keep_lines = False
for line in contents:
    data=line.split("/")
    last= len(data)-1
    if data[last]:
        branch_list.append(data[last])



print branch_list
print git_branch(branch_list)
