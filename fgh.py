#!/usr/bin/env python2

import sys
import argparse

import subprocess
PIPE = subprocess.PIPE


# gh pr create -R github.ibm.com/openbmc/openbmc -B 1020-ghe -b '' -t "1020-ghe: pldm: downstream srcrev bump 45c48376f1..f6ed9a6e6a"
def git_show(parms_array):
    git_args = ['git', 'show']+parms_array

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()

    if stderroutput:
        print "There is an ERROR in git_show:"
        print(stderroutput)
        print "end ERROR ouput"

    return stdoutput

def git_log(parms_array):

    git_args = ['git', 'log']+parms_array

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()

    if stderroutput:
        print "There is an ERROR in git_log:"
        print(stderroutput)
        print "end ERROR ouput"
    return stdoutput


def gh_pr_create(Repo, Branch, body, title):
    gh_args = ['gh', 'pr', 'create', '-R', Repo, '-B', Branch, '-b', body, '-t', title]

    process = subprocess.Popen(gh_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()

    if stderroutput:
        print "There is an ERROR in gh_pr_create:"
        print(stderroutput)
        print "end ERROR ouput"

    print(stdoutput)

def gh_pr_edit(PR_number, Repo, body, title):
    gh_args = ['gh', 'pr', 'edit', PR_number, '-R', Repo, '-b', body, '-t', title]

    process = subprocess.Popen(gh_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()

    if stderroutput:
        print "There is an ERROR in gh_pr_create:"
        print(stderroutput)
        print "end ERROR ouput"

    print(stdoutput)

def parse_arguments(i_args):

    app_description = '''wrapper for gh   '''

    l_parser = argparse.ArgumentParser(description=app_description)
    l_parser.add_argument(
        '-R', '--repo', default='github.ibm.com/openbmc/openbmc', 
        help='-R, --repo [HOST/]OWNER/REPO   Select repository using the [HOST/]OWNER/REPO format')
    l_parser.add_argument(
        '-B', '--branch', default='1020-ghe', 
        help='-B, --branch The branch into which you want your code merged')
    l_parser.add_argument(
        '-b', '--body', default='commit', 
        help='-b, --body Body for the pull request')    
    l_parser.add_argument(
        '-t', '--title', default='commit', 
        help='-t, --title title for the pull request')
    l_parser.add_argument(
        '-n', '--n_entries', default=1, 
        help='-n, --n_entries number of log commit entries to add to title and body')
    l_parser.add_argument(
        '-d', '--dry-run', dest='dry_run', action='store_true',
        help='perform a dry run only')
    l_parser.add_argument(
        '-e', '--edit', default='',
        help='perform a edit ')

    l_parser.add_argument(
        '-v', '--verbose', dest='noisy', action='store_true',
        help='enable verbose status messages')
    l_parser.add_argument(
        '-o', '--org', default='ibm-openbmc', 
        help='set org value to scan for')

    return l_parser.parse_args(i_args)


def main(i_args):
    # Parse the arguments
    l_args = parse_arguments(i_args)
    title=l_args.title
    body=l_args.body

    if (l_args.title == 'commit'):
        number = '-n {}'.format(l_args.n_entries)
        shas = git_log([number, '--pretty=format:%h']).split()
        
        title="{}: ".format(l_args.branch)
        for sha in shas:
            parms = [sha,'--pretty=format:%s', '-s']
            title+=git_show(parms)
            if sha != shas[-1]:
                title+=' & '

    if (l_args.body == 'commit'):
        number = '-n {}'.format(l_args.n_entries)
        shas = git_log([number, '--pretty=format:%h']).split()
        commit_title=""
        body=""
        for sha in shas:
            parms = [sha,'--pretty=format:%s', '-s']
            commit_title=git_show(parms)
            body += "#### {}\r\n```\r\n".format(commit_title)
            parms = [sha,'--pretty=format:%b', '-s']
            body+=git_show(parms)
            body+='```'
            if sha != shas[-1]:
                body+='\r\n'


    if l_args.dry_run:
        if l_args.edit:
            message_args = (l_args.edit,l_args.repo,l_args.branch,body,title )
            print ("gh pr edit {} -R {} -B {} -b '{}' -t '{}'".format(*message_args))
        else:
            message_args = (l_args.repo,l_args.branch,body,title )
            print("gh pr create -R {} -B {} -b '{}' -t '{}'".format(*message_args))

    else:
        if l_args.edit:
            gh_pr_edit(l_args.edit, l_args.repo, body, title)
        else:
            gh_pr_create(l_args.repo, l_args.branch, body, title)



if __name__ == '__main__':
    main(sys.argv[1:])
