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
    print stderroutput
    return stdoutput

def git_log(parms_array):

    git_args = ['git', 'log']+parms_array

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()

    if 'fatal' in  stdoutput:
        print('fatal')
    else:
        return stdoutput

    return []


def gh_pr_create(Repo, Branch, body, title):
    gh_args = ['gh', 'pr', 'create', '-R', Repo, '-B', Branch, '-b', body, '-t', title]

    process = subprocess.Popen(gh_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
#    print(stderroutput)
    if 'fatal' in  stdoutput:
        print('git_show fatal')
    else:
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
        '-s', '--sha', default=git_log(['-n 1', '--pretty=format:%h']), 
        help='-s, --sha sha commit information to use in creating PR')
    l_parser.add_argument(
        '-d', '--dry-run', dest='dry_run', action='store_true',
        help='perform a dry run only')
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
        parms = [l_args.sha,'--pretty=format:%s', '-s']
        title="{}: ".format(l_args.branch)
        title+=git_show(parms)

    if (l_args.body == 'commit'):
        parms = [l_args.sha,'--pretty=format:%b', '-s']
        body = "#### {}\r\n```\r\n".format(title)
        body+=git_show(parms)
        body+='```'

    if l_args.dry_run:
        message_args = (l_args.repo,l_args.branch,body,title )
        print("gh pr create -R {} -B {} -b '{}' -t '{}'".format(*message_args))

    else:
        gh_pr_create(l_args.repo, l_args.branch, body, title)



if __name__ == '__main__':
    main(sys.argv[1:])
