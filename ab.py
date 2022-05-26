#!/usr/bin/env python3

from github import Github
import config
import re

import argparse
import os
#import sh
import sys
import math
import subprocess
PIPE = subprocess.PIPE

try:
    import git
    from git import GitCommandError
    HAVE_GIT = True
except ImportError:
#    _log.debug('Failed to import git module')
    HAVE_GIT = False

def log(msg, args):
    if args.noisy:
        sys.stderr.write('{}\n'.format(msg))

def extract_project_from_uris(i_args, uris):
    # remove SRC_URI = and quotes (does not handle escaped quotes)
    uris = uris.split('"')[1]
    for uri in uris.split():
        remote = i_args.remote + '/' + i_args.org
        if remote not in uri:
            continue

        # remove fetcher arguments
        uri = uri.split(';')[0]
        # the project is the right-most path segment
        return uri.split('/')[-1].replace('.git', '')

    return None

def extract_sha_from_recipe(args, recipe):
    with open(recipe) as fp:
        uris = ''
        project = None
        sha = None
        if args.project_name == "linux":
            project = 'linux'
        for line in fp:
            line = line.rstrip()
            if 'SRCREV' in line:
                sha = line.split('=')[-1].replace('"', '').strip()
            elif not project and uris or '_URI' in line:
                uris += line.split('\\')[0]
                if '\\' not in line:
                    # In uris we've gathered a complete (possibly multi-line)
                    # assignment to a bitbake variable that ends with _URI.
                    # Try to pull an OpenBMC project out of it.
                    project = extract_project_from_uris(args, uris)
                    if project is None:
                        # We didn't find a project.  Unset uris and look for
                        # another bitbake variable that ends with _URI.
                        uris = ''

            if project and sha:
                return (project, sha)

        print('No SRCREV or URI found in {}'.format(recipe))
        return(project, sha)

def git_add(recipe):

    git_args = ['git', 'add', recipe]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if 'fatal' in  stdoutput:
        print('git_add fatal')

def git_commit(commit_msg):

    git_args = ['git', 'commit', '-m', commit_msg]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if 'fatal' in  stdoutput:
        print('git_commit fatal')
        
def git_show(sha):
    git_args = ['git', 'show', sha]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if 'fatal' in  stdoutput:
        print('git_show fatal')
    else:
        print(stdoutput)

def git_log(parms_array):

    git_args = ['git', 'log']+parms_array

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()

    if 'fatal' in  stdoutput:
        print('fatal')
    else:
        return stdoutput

    return []

def find_recipes(i_args):
    
    git_args = ['git','--no-pager','grep','-l', '-e', '_URI', '--and', '-e', i_args.remote+'/'+i_args.org]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if 'fatal' in  stdoutput:
        print('fatal')
    else:
        return stdoutput.decode('utf-8').split()

    return []

def find_and_process_bumps(args):
    project_sha = args.project_sha
    if args.project_name == "linux":
        candidate_recipes = ['meta-aspeed/recipes-kernel/linux/linux-aspeed_git.bb']
    else:
        candidate_recipes = find_recipes(args)
    for recipe in candidate_recipes:
        project_name, recipe_sha = extract_sha_from_recipe(args, recipe)
        if project_name in args.project_name:
            if args.dry_run:
                print(project_name)
                print(recipe)
            recipe_basename = os.path.basename(recipe) 
            if project_sha == recipe_sha:
                banner = "!*!*!*!*!*!*!*!*!*!*!*!*!*!*!*!*!*!*!*!*!*"
                message_args = (banner,recipe_basename, recipe_sha[:10],banner)
                print("\n{}\n\n{} is up to date ({})\n\n{}\n\n".format(*message_args))
                continue
        
            recipe_content = None
            with open(recipe) as fd:
                recipe_content = fd.read()
            if not args.dry_run: 

                recipe_content = recipe_content.replace(recipe_sha, project_sha)
                with open(recipe, 'w') as fd:
                    fd.write(recipe_content)
            
                git_add(recipe)
            if args.project_name == "linux":
                linux_recipe = 'meta-aspeed/recipes-kernel/linux/linux-aspeed.inc'
                with open(linux_recipe) as fd:
                    recipe_content = fd.read()

            l_uri = get_uri_info(recipe_content)
            if l_uri:
                l_repo = get_repo(l_uri)
            else:
                continue

            l_commits = l_repo.compare(recipe_sha, project_sha).commits

            # Go through all commits check for duplicates
            commit_msg_dict = dict()
            for l_commit in l_commits:
                commit_msg_dict.setdefault(l_commit.commit.message.encode('ascii','ignore'), []).append(l_commit.sha)

            
            commit_dict = dict()
            for l_commit in l_commits:
                # if the sha does match the last one in the key list it's a duplicate so continue to the next commit. 
                if ((commit_msg_dict[l_commit.commit.message.encode('ascii','ignore')][-1]) != l_commit.sha):
                    continue

                l_author = l_commit.commit.author
                l_summary = l_author.name + " " + (l_commit.commit.message).split('\n')[0]
                commit_dict.setdefault(l_author.name.encode('ascii','ignore'), []).append((l_commit.commit.message).split('\n')[0])

            shortlog = ''
            for key in commit_dict:
                l_len = len(commit_dict[key])
                shortlog += '{} ({}):\n'.format(key,l_len)
                for commit_msg in commit_dict[key]:
                    shortlog += '  {}\n'.format(commit_msg)
                shortlog += '\n'

            location = ""
            if args.org == "ibm-openbmc":
                location = " downstream"
            if args.remote == "github.ibm.com":
                location = " ghe"

            commit_summary_args = (project_name, location, recipe_sha[:10], project_sha[:10])
            commit_msg = '{}:{} srcrev bump {}..{}'.format(*commit_summary_args)
            commit_msg += '\n\n{}'.format(shortlog)
                
            if  not args.dry_run:
                git_commit(commit_msg)
            else:
                print("dry run")
                print(commit_msg)

def parse_arguments(i_args):

    app_description = '''Local recipe bumping tool.
Find bitbake metadata files (recipes) that use the git.ibm.com
and check the project repository for given revision.
Generate commits that update bitbake metadata files with SRCREV
if given revision is new
Generate commit.
    '''

    l_parser = argparse.ArgumentParser(description=app_description)
    l_parser.add_argument(
        'project_name',
        help='target project name to change sha')
    l_parser.add_argument(
        'project_sha',
        help='input sha commit length 40 digits')
    l_parser.add_argument(
        '-d', '--dry-run', dest='dry_run', action='store_true',
        help='perform a dry run only')
    l_parser.add_argument(
        '-v', '--verbose', dest='noisy', action='store_true',
        help='enable verbose status messages')
    l_parser.add_argument(
        '-r', '--remote', default='github.com', 
        help='set remote value to scan for')
    l_parser.add_argument(
        '-o', '--org', default='ibm-openbmc', 
        help='set org value to scan for')

    return l_parser.parse_args(i_args)

###############################################################################
# @brief remove end of a string
#
# @param thestring  : String to check
# @param ending     : remove if the ending matches end of string to check
###############################################################################

def rchop(thestring, ending):
    if thestring.endswith(ending):
        return thestring[:-len(ending)]
    return thestring

###############################################################################
# @brief Updates the repo under the given path or clones it from the
#        uri if it doesn't yet exist
#
# @param i_uri  : The URI to the remote repo to clone
# @param i_path : The file path to where the repo currently exists or
#                 where it will be created
###############################################################################
def get_repo(i_uri):

    l_uri = i_uri.strip()
    l_values = l_uri.split('/')

    count = 0;
    for l_value in l_values:
        if 'github.ibm.com' in l_value:
            l_repo_name = l_values[count+1] + "/" + rchop(l_values[count+2],'.git')
            print(l_repo_name)
            l_github = Github(login_or_token = config.py_ibm_token, base_url='https://github.ibm.com/api/v3')
            l_repo = l_github.get_repo(l_repo_name)
        
        elif 'github.com' in l_value:
            l_repo_name = l_values[count+1] + "/" + l_values[count+2]
            l_repo_name = rreplace(l_repo_name, ".git", '', 1)
            print(l_repo_name)
            l_github = Github(login_or_token = config.py_token)
            l_repo = l_github.get_repo(l_repo_name)
        count += 1


    return l_repo

def get_uri_info(recipe):


    # Get the URI of the subrepo
    l_uri = None
    l_uri_match = re.search('KSRC[+=? ]+"([-a-zA-Z0-9/:\.@]+);', recipe)
    if l_uri_match:
        l_uri = l_uri_match.group(1)

    l_uri_match = re.search('_URI[+=? ]+"([-a-zA-Z0-9/:\.]+)"', recipe)
    if l_uri_match:
        l_uri = l_uri_match.group(1)

    l_uri_match = re.search('_URI[+=? ]+"([-a-zA-Z0-9/:\.@]+);', recipe)
    if l_uri_match:
        l_uri = l_uri_match.group(1)


    l_uri_match = re.search('\+SRC_URI[+=? ]+"([-a-zA-Z0-9/:\.@]+);', recipe)
    if l_uri_match:
        l_uri = l_uri_match.group(1)

    return l_uri

###############################################################################
# @brief replaces number of matches from reverse 
#
# @param s_value   : string buffer
# @param old       : find value
# @param new       : replace with value
# @param occurence : number of times to replace. 
#
# @return The title of the issue
###############################################################################
def rreplace(s_value, old, new, occurrence):
    line = s_value.rsplit(old, occurrence)
    return new.join(line)


def main(i_args):
    # Parse the arguments
    l_args = parse_arguments(i_args)


    digits = len(str(l_args.project_sha))
    if digits != 40:
        message_args = (l_args.project_sha, digits)
        print('sha number {}  is {} not 40'.format(*message_args))
        exit(1)

    find_and_process_bumps(l_args)

    if not l_args.dry_run:
        log_sha = git_log(['-n 1', '--pretty=format:%h'])
        git_show(log_sha)



if __name__ == '__main__':
    main(sys.argv[1:])
