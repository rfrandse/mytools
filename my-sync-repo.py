#!/usr/bin/env python2

##
#
##

###############################################################################
# @file sync-repo
# @brief sync source repo to target repo master
###############################################################################

import argparse
from argparse import RawDescriptionHelpFormatter
import git
import json
import logging
import os
import re
import requests
import sys

from github_repository import CreateRepo


def fread(FILE):
    l_record_data = None
    if os.path.isfile(FILE):
        with open(FILE,"r") as json_file:
            l_record_data = json.load(json_file)

    return l_record_data

def fwrite(FILE, record_data):
    with open(FILE, 'w') as fp:
        json.dump(record_data, fp, indent=4, default=str)

###############################################################################
# @brief Updates the repo under the given path or clones it from the
#        uri if it doesn't yet exist
#
# @param i_uri  : The URI to the remote repo to clone
# @param i_path : The file path to where the repo currently exists or
#                 where it will be created
###############################################################################
def clone_or_update_source(i_uri, i_repo_name, i_repo_location, i_remote, i_repo_branch):

    logging.info("clone_or_update_source i_uri=%s i_repo_name=%s" % (i_uri, i_repo_name))
    logging.debug("i_repo_location=%s" % i_repo_location)
    logging.debug("i_repo_location=%s" % i_repo_location)
    logging.debug("i_remote=%s" % i_remote) 
    logging.debug("i_repo_branch=%s" % i_repo_branch)

    # If the repo exists, just update it
    if os.path.isdir(i_repo_location):

        logging.info('%s repo exists at %s', i_repo_name, i_repo_location)

        # refresh
        l_repo = git.Repo(i_repo_location)
        l_repo.git.fetch(i_remote, i_repo_branch)
        l_repo.git.checkout(i_repo_branch)
        l_repo.git.pull(i_remote, i_repo_branch)

    else:
        logging.info('cloning repo:%s at %s branch=%s', i_repo_name, i_repo_location, i_repo_branch)
        os.mkdir(i_repo_location)
        l_repo = git.Repo.clone_from(i_uri,i_repo_location,branch=i_repo_branch)

def sync_repos(i_parms):

    if os.path.isdir(i_parms.repo_path):
        os.chdir(i_parms.repo_path)
        logging.info('Changing WORKSPACE:%s', i_parms.repo_path)
    else:
        logging.critical('WORKSPACE:%s does not exist', i_parms.repo_path)
        sys.exit()

    if i_parms.target_repo_name is None:
        i_parms.target_repo_name = i_parms.repo_name
    if i_parms.repo_dir_name is None:
        i_parms.repo_dir_name = i_parms.repo_name

    logging.debug(i_parms)

    l_source_repo_uri = 'git@%s:%s/%s.git' % (i_parms.source_domain,
                                              i_parms.source_project,
                                              i_parms.repo_name)
    l_repo_location = os.path.join(i_parms.repo_path, i_parms.repo_dir_name)

    logging.debug(l_repo_location)

    # Get the repo that the user requested
    # if it's a new clone target branch master
    # if it already exists refresh from origin/master
    clone_or_update_source(l_source_repo_uri,
                           i_parms.repo_name,
                           l_repo_location,
                           'origin',
                           'master')
    try:
        l_repo = git.Repo(l_repo_location)
    except git.exc.InvalidGitRepositoryError:
        logging.critical(str(l_repo_location) + ' not a valid git repository')
        sys.exit()


    downstream = None
    my_remote = None
    ghe_remote = None
    for Remote in l_repo.remotes:
        if 'ds' == Remote.name:
            downstream = Remote
            logging.debug("found downstream(ds) remote")
        if 'mypr' == Remote.name:
            my_remote = Remote
            logging.debug("found mypr remote")
        if 'ghe' == Remote.name:
            ghe_remote = Remote
            logging.debug("found ghe remote")


    l_target_repo_uri = 'git@%s:%s/%s.git' % (i_parms.target_domain,
                                              i_parms.target_project,
                                              i_parms.target_repo_name)

    downstream_repo_uri = 'git@%s:%s/%s.git' % ('github.com', 
                                               'ibm-openbmc', 
                                               i_parms.target_repo_name)
    l_mypr_repo_uri = 'git@%s:%s/%s.git' % (i_parms.target_domain,
                                            'rfrandse',
                                            i_parms.target_repo_name)

    ghe_repo_uri = 'git@%s:%s/%s.git' % ('github.ibm.com',
                                         'openbmc',
                                         i_parms.target_repo_name)

    if downstream is None:
        downstream = l_repo.create_remote('ds', url=downstream_repo_uri)

    if my_remote is None:
        my_remote = l_repo.create_remote('mypr', url=l_mypr_repo_uri)

    if ghe_remote is None:
        ghe_remote = l_repo.create_remote('ghe', url=ghe_repo_uri)


    try:
        l_repo.git.ls_remote(l_target_repo_uri)
    except git.exc.GitCommandError:
        logging.warning(str(l_target_repo_uri) +
                        ' does not exist. Creating remote repo')

        github_repo = CreateRepo(i_parms.target_repo_name, 
                ftype='org',
                project=i_parms.target_project,
                i_base_url=i_parms.github_url,
                i_token=i_parms.target_token)

        # ok a new upstream repo was created. 
    # cheeck origin and reset if needed the origin remote to point at openbmc opensource
    origin_repo_uri = 'git@%s:%s/%s.git' % ('github.com',
                                        'openbmc',
                                        i_parms.target_repo_name)

    current_origin_remote = l_repo.git.remote('get-url','origin')
    logging.debug(current_origin_remote)

    if (current_origin_remote != origin_repo_uri):
        
        origin_repo_uri = 'git@%s:%s/%s.git' % ('github.com',
                                        'openbmc',
                                        i_parms.target_repo_name)
        l_repo.git.remote('remove','origin')
        l_repo.git.remote('add', 'origin', origin_repo_uri)
        l_repo.git.remote('set-url', '--push', 'origin', 'null')
        l_repo.git.fetch('origin','--set-upstream', 'master')
#        l_repo.git.branch('-u', 'origin/master')


    if (i_parms.target_domain == 'github.ibm.com'):
        ghe_remote.push()
       
    elif (i_parms.target_project == 'ibm-openbmc'):
        downstream.push()
        

    


#    if i_parms.remote_branch is not 'master':

    remote_name = 'origin'
    if (i_parms.source_domain == 'github.com'):
        if (i_parms.source_project == 'ibm-openbmc'):
            remote_name = 'ds'
    if (i_parms.source_domain == 'github.ibm.com'):
        remote_name = 'ghe'
    clone_or_update_source(l_source_repo_uri,
                       i_parms.repo_name,
                       l_repo_location,
                       remote_name,
                       i_parms.remote_branch)
    if i_parms.remote_branch is not 'master':

        if (i_parms.target_domain == 'github.ibm.com'):
            ghe_remote.push()
           
        elif (i_parms.target_project == 'ibm-openbmc'):
            downstream.push()
            downstream.push('--tags')



''' 
        try:
            heads = l_repo.git.ls_remote('--heads','origin')
        except git.exc.GitCommandError:
            logging.error('remote origin does not exist.')
            sys.exit()
        if  i_parms.remote_branch in heads:
            
            logging.debug("heads=%s" % heads)
            l_heads = heads.splitlines()


            l_remote_branch = None
#            for l_head in l_heads:
#                logging.debug("l_head=%s" % l_head)
#                if i_parms.remote_branch in l_head:
#                    l_remote_branch = l_head

            for ref in l_repo.refs:
                logging.debug("ref=%s" % ref)
                if 'origin' in str(ref):
                    if i_parms.remote_branch in str(ref):
                        l_remote_branch = ref


            logging.debug("l_remote_branch=%s" % l_remote_branch)

#            branch_name = "-b"
            l_repo.git.checkout(l_remote_branch, '-b', i_parms.remote_branch)
            l_repo.create_head(i_parms.remote_branch, l_remote_branch) \
            .set_tracking_branch(l_remote_branch)

#            l_repo.create_head('master', origin.refs.master) \
#            .set_tracking_branch(origin.refs.master)
#            origin.pull()
#            sys.exit()
            downstream_head = "HEAD:%s" % i_parms.remote_branch

            downstream.push(downstream_head)
            logging.info('pushed %s branch to remote' % l_remote_branch)

'''


###############################################################################
# @brief Main function for the script
#
# @param i_args : Command line arguments
###############################################################################
def main(i_args):
     # Parse the arguments
    l_args = parse_arguments(i_args)

# Set the logger level
# DEBUG   Detailed information, typically of interest only when diagnosing
#         problems.
# INFO    Confirmation that things are working as expected.
# WARNING An indication that something unexpected happened, or
#         indicative of some problem in the near future (e.g. 'disk space low')
#         The software is still working as expected.
# ERROR   Due to a more serious problem, the software has been able to perform
#         some function.
# CRITICAL A serious error, indicating that the program itself may be unable to
#          continue running.
    loglevel = l_args.log
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level)

    sync_repos(l_args)
    save_config(l_args)

    return

###############################################################################
# @brief Save config to fiel
#
# @param i_args : List of arguments to save to config
#
# @return none
###############################################################################
def save_config(i_args):
    l_config = {}
    for item in vars(i_args):
#       print (item, getattr(i_args,item))
       l_config[item] = getattr(i_args,item)
    
    fwrite(l_config["save_config"],l_config)

###############################################################################
# @brief Parses the arguments from the command line
#
# @param i_args : The list of arguments from the command line, excluding the
#                 name of the script
#
# @return An object representin the parsed arguments
###############################################################################
def parse_arguments(i_args):
    config_parser = argparse.ArgumentParser(description='Compile database script', add_help=False)
    # JSON support
    config_parser.add_argument('--json_file',default="last_config.json", help='Configuration JSON file default=last_config.json')
    l_args, left_argv = config_parser.parse_known_args()
    if l_args.json_file:
        config = fread(l_args.json_file)
        if config is None:
            config = {}
    else:
        config = {}

    l_parser = argparse.ArgumentParser(parents=[config_parser],
        description='Synchronizes source repository to a target repository. \n'
                    + 'If target repository does not exist target repo is '
                    + 'created.\n'
                    + 'Use sync_config.py to setup default values.\n'
                    + 'For example:\n'
                    + 'base_path=</esw/san5/[user name]>\n'
                    + 'source_token=<authentication token>\n'
                    + 'target_token=<authentication token>\n'
                    + 'source_domain=<domain name> [github.com]\n'
                    + 'target_domain=<domain name>\n'
                    + 'source_api_url=<https://github.com/api/v3>\n'
                    + 'target_api_url=<https://[target domain name]/api/v3>\n'
                    + 'source_project=<openbmc>\n'
                    + 'target_project=<openbmc>\n',
                    formatter_class=RawDescriptionHelpFormatter)
    l_parser.add_argument(
        'repo_name',
        help='The name of the repo.')
    l_parser.add_argument(
        '--target_repo_name', '-tr',
        default=None,
        help='The name of the target repo '
             + 'default: same as repo name')
    l_parser.add_argument(
        '--repo_path',
        default=config.get("repo_path"),
        help='The main path of the cloned repo. '
             + 'Consider this the parent directory default from config file')
    l_parser.add_argument(
        '--repo_dir_name',
        default=None,
        help='The directory name of the cloned repo. Default is repo_name'
             + 'This is to prevent overwriting cloned repos of the same name')
    l_parser.add_argument(
        '--source_domain',
        default=config.get("source_domain"),
        help='source domain default from configfile '
             + '')
    l_parser.add_argument(
        '--target_domain',
        default=config.get("target_domain"),
        help='target domain default from config file ')
    l_parser.add_argument(
        '--source_project',
        default=config.get("source_project"),
        help='source project, example: openbmc default from config file')
    l_parser.add_argument(
        '--target_project',
        default=config.get("target_project"),
        help='target project default from config file')    
    l_parser.add_argument(
        '--remote_branch',
        default='master',
        help='remote branch default=master')
    l_parser.add_argument(
        '--save_config',
        default='last_config.json',
        help='save config file, default=last_config.json')
    l_parser.add_argument(
        '-L', '--log',
        default="INFO",
        help='Set log level: DEBUG, INFO, WARNING, ERROR, CRITICAL'
             + 'default=INFO Example: --log=DEBUG ')
    l_parser.add_argument(
        '--github_url',
        default=config.get("github_url"),
        help='github url default from config file')
    l_parser.add_argument(
        '--target_token',
        default=config.get("target_token"),
        help='token for target github repo default from config file')

    return l_parser.parse_args(i_args)

'''
    l_parser = argparse.ArgumentParser(parents=[config_parser],
        description='Synchronizes source repository to a target repository. \n'
                    + 'If target repository does not exist target repo is '
                    + 'created.\n'
                    + 'Use sync_config.py to setup default values.\n'
                    + 'For example:\n'
                    + 'base_path=</esw/san5/[user name]>\n'
                    + 'source_token=<authentication token>\n'
                    + 'target_token=<authentication token>\n'
                    + 'source_domain=<domain name> [github.com]\n'
                    + 'target_domain=<domain name>\n'
                    + 'source_api_url=<https://github.com/api/v3>\n'
                    + 'target_api_url=<https://[target domain name]/api/v3>\n'
                    + 'source_project=<openbmc>\n'
                    + 'target_project=<openbmc>\n',
                    formatter_class=RawDescriptionHelpFormatter)
    l_parser.add_argument(
        'repo_name',
        help='The name of the repo.')
    l_parser.add_argument(
        '--source_domain',
        default=config.get("source_domain"),
        help='source domain default github.com '
             + '')
    l_parser.add_argument(
        '--target_domain',
        default=config.get("target_domain"),
        help='target domain ')

    l_parser.add_argument(
        '-L', '--log',
        default="INFO",
        help='Set log level: DEBUG, INFO, WARNING, ERROR, CRITICAL'
             + 'default=INFO Example: --log=DEBUG ')
#    return l_parser.parse_args(left_argv)    
    return l_parser.parse_args(i_args)



'''

# Only run main if run as a script
if __name__ == '__main__':
    main(sys.argv[1:])
