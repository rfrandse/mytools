#!/usr/bin/env python2


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
        print('fatal')

def git_commit(commit_msg):

    git_args = ['git', 'commit', '-m', commit_msg]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if 'fatal' in  stdoutput:
        print('fatal')
        
def git_show(sha):
    git_args = ['git', 'show', sha]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if 'fatal' in  stdoutput:
        print('fatal')
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
    candidate_recipes = find_recipes(args)
    for recipe in candidate_recipes:
        project_name, recipe_sha = extract_sha_from_recipe(args, recipe)
        if project_name in args.project_name:
            if args.dry_run:
                print project_name
                print recipe
            recipe_basename = os.path.basename(recipe) 
            if project_sha == recipe_sha:
                message_args = (recipe_basename, recipe_sha[:10])
                print('{} is up to date ({})'.format(*message_args))
                continue
        
            if not args.dry_run:        
                recipe_content = None
                with open(recipe) as fd:
                    recipe_content = fd.read()

                recipe_content = recipe_content.replace(recipe_sha, project_sha)
                with open(recipe, 'w') as fd:
                    fd.write(recipe_content)
            
                git_add(recipe)

            commit_summary_args = (project_name, recipe_sha[:10], project_sha[:10])

            commit_msg = '{}: downstream srcrev bump {}..{}'.format(*commit_summary_args)

            if  not args.dry_run:
                git_commit(commit_msg)
            else:
                print "dry run"
                print commit_msg

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
