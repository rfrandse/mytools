#!/usr/bin/env python2

import sys
import argparse
import logging 
import re
import requests
from datetime import datetime, timedelta

from github import Github
import config
import os
import json
import subprocess
PIPE = subprocess.PIPE

workspace_dir = os.getcwd()


def rchop(thestring, ending):
    if thestring.endswith(ending):
        return thestring[:-len(ending)]
    return thestring

def rreplace(s_value, old, new, occurrence):
    line = s_value.rsplit(old, occurrence)
    return new.join(line)


def get_repo_info(recipe):


    # Get the address location of the subrepo
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

def get_bump_info(i_file, i_repo):

    # Get the new and old version hashes
    l_old_hash = None
    l_new_hash = None
    l_old_hash_match = re.search('-[A-Z_]*SRCREV[+=? ]+"([a-f0-9]+)"',
                                 i_file.patch)
    l_new_hash_match = re.search('\+[A-Z_]*SRCREV[+=? ]+"([a-f0-9]+)"',
                                 i_file.patch)
    if l_old_hash_match:
        l_old_hash = l_old_hash_match.group(1)
    if l_new_hash_match:
        l_new_hash = l_new_hash_match.group(1)

    # Get the URI of the subrepo
    l_uri = None
    l_uri_match = re.search('_URI[+=? ]+"([-a-zA-Z0-9/:\.]+)"', i_file.patch)
    if l_uri_match:
        l_uri = l_uri_match.group(1)

    l_uri_match = re.search('_URI[+=? ]+"([-a-zA-Z0-9/:\.@]+);', i_file.patch)
    if l_uri_match:
        l_uri = l_uri_match.group(1)


    l_uri_match = re.search('\+SRC_URI[+=? ]+"([-a-zA-Z0-9/:\.@]+);', i_file.patch)
    if l_uri_match:
        l_uri = l_uri_match.group(1)

    return l_uri, l_new_hash, l_old_hash


def get_repo(i_uri):

    l_uri = i_uri.strip()
    l_values = l_uri.split('/')

    count = 0;
    l_repo = None
    for l_value in l_values:
        if 'github.ibm.com' in l_value:
            l_repo_name = l_values[count+1] + "/" + rchop(l_values[count+2],'.git')
            logging.info('{}'.format(l_repo_name))
            l_github = Github(login_or_token = config.py_ibm_token, base_url='https://github.ibm.com/api/v3')
            l_repo = l_github.get_repo(l_repo_name)
        
        elif 'github.com' in l_value:
            l_repo_name = l_values[count+1] + "/" + l_values[count+2]
            l_repo_name = rreplace(l_repo_name, ".git", '', 1)                
            logging.info('{}'.format(l_repo_name))
            l_github = Github(login_or_token = config.py_token)
            l_repo = l_github.get_repo(l_repo_name)
        count += 1


    return l_repo

###############################################################################
# @class CommitReport
# @brief A class representing information about a commit and all commits in
#        relevant subrepos
###############################################################################
class CommitReport:
    def __init__(self, i_repo_uri, i_repo_name,  i_sha, i_nice_name, i_author_name,
                 i_summary, i_insertions, i_deletions, i_closed_issues, i_notes):
        self.repo_uri = i_repo_uri
        self.repo_name = i_repo_name
        self.sha = i_sha
        self.nice_name = i_nice_name
        self.author_name = i_author_name
        self.summary = i_summary
        self.insertions = i_insertions
        self.deletions = i_deletions
        self.closed_issues = i_closed_issues
        self.notes = i_notes
        self.subreports = []

    def to_cl_string(self, i_level=0):
        # Define colors for the console
        RED = '\033[31m'
        BLUE = '\033[94m'
        ENDC = '\033[0m'
        # Put the string together
        l_cl_string = ('  ' * i_level) + RED + self.repo_name + ENDC  + ' ' \
            + BLUE + self.nice_name + ENDC + ' ' \
            + self.author_name + ' ' \
            + re.sub('\s+', ' ', self.summary)
        # Do the same for every subreport
        for l_report in self.subreports:
            l_cl_string += '\n' + l_report.to_cl_string(i_level + 1)
        return l_cl_string
    def to_string(self, i_level=0):
        # Define colors for the console
        # Put the string together
        l_string = ('  ' * i_level) + self.repo_name + ' ' \
            + self.nice_name + ' ' \
            + self.author_name + ' ' \
            + re.sub('\s+', ' ', self.summary)
        # Do the same for every subreport
        for l_report in self.subreports:
            l_string += '\n' + l_report.to_string(i_level + 1)
        return l_string

    def to_html(self, i_level=0):
        l_repo_url = re.sub('git://', 'http://', self.repo_uri)
        l_repo_url = re.sub('github.ibm.com', 'https://github.ibm.com', self.repo_uri)
        # Get HTML for this commit
        l_html = \
            '<div style="margin-left: ' + str(i_level * 20) + 'px">' \
            + '<a href="' + l_repo_url + '" target="_blank" ' \
            + 'style="color: red">' + self.repo_name + '</a>&nbsp;' \
            + '<a href="' + l_repo_url + '/commit/' + self.sha \
            + '" target="_blank" style="color: blue">' + self.nice_name \
            + '</a>&nbsp;' \
            + '<span style="color: green">' \
            + re.sub('\s+', ' ', self.author_name) + '</span>' + ' ' \
            + '<span>' + re.sub('\s+', ' ', self.summary) + '</span>' \
            + '</div>\n'
        # Get the HTML for all subcommits
        for l_commit in self.subreports:
            l_html += l_commit.to_html(i_level + 1)
        return l_html

    def get_total_insertions(self):
        l_insertions = self.insertions
        for l_commit in self.subreports:
            l_insertions += l_commit.get_total_insertions()
        return l_insertions

    def get_total_deletions(self):
        l_deletions = self.deletions
        for l_commit in self.subreports:
            l_deletions += l_commit.get_total_deletions()
        return l_deletions

    def get_all_closed_issues(self):
        l_closed_issues = self.closed_issues
        for l_commit in self.subreports:
            l_closed_issues.extend(l_commit.get_all_closed_issues())
        return l_closed_issues
    def get_all_notes(self):
        l_notes = self.notes
        for l_commit in self.subreports:
            l_notes.extend(l_commit.get_all_notes())
        return l_notes


##############################################################################
# @brief Cuts the hash in commit revision names down to its 7 digit prefix
#
# @param i_name_rev : The name of the revision to change
#
# @return The same revision name but with the hash its 7 digit prefix instead
###############################################################################
def to_prefix_name_rev(i_name_rev):
    l_name_rev = i_name_rev[0:7]
#    l_hash, l_name = l_name_rev.split()
#    l_name_rev = l_hash[0:7] + ' ' + l_name
    return l_name_rev

def get_closed_issues(i_repo, i_commit):

    l_closed_issues = []
    l_notes = []

    #Get the PR number from the title
    l_summary = ((i_commit.commit.message).split('\n')[0]).strip()   
    logging.info(i_commit.commit.url)
    pr_url = rreplace(i_commit.commit.url, "/git", '', 1)     
    pr_url += "/pulls"
    logging.info(pr_url)
    pull_data = None
    if 'github.ibm.com' in i_commit.commit.url:
        logging.info("processing github.ibm.com")
        logging.info(l_summary)
        num_match = re.search('\(#([0-9]+)\)$',l_summary)
        if num_match:
            pr_number = int(num_match.group(1))
#            print pr_number
            pull_data = i_repo.get_pull(pr_number)
            cq_matches = re.findall('fixes.+([S|F]W[0-9]+).*',pull_data.body,flags=re.I)
            if cq_matches:
                for cq in cq_matches:
                    link='[{}](https://w3.rchland.ibm.com/projects/bestquest/?defect={})'.format(cq,cq)
                    l_closed_issues.append(link)
            pull_comments = pull_data.get_issue_comments()
            for comment in pull_comments:
#                print comment.body
                #cq_matches = re.findall('fixes[: ]+([S|F]W[0-9]+)',comment.body,flags=re.I)
                cq_matches = re.findall('fixes.+([S|F]W[0-9]+).*',comment.body,flags=re.I)
                if cq_matches:
                    for cq in cq_matches:
                        link='[{}](https://w3.rchland.ibm.com/projects/bestquest/?defect={})'.format(cq,cq)
                        l_closed_issues.append(link)
                release_notes = re.search(r'Release note[: ](.*)',comment.body,flags=re.I | re.DOTALL)
                if release_notes:
                    lines =  release_notes.group(1).splitlines()
                    for line in lines:
                        if "::" in line:
                            note = line.split('::')
                            l_notes.append(note[0].encode("utf8").strip())
                            break
                        else:
                            l_notes.append(line.encode("utf8").strip())

        num_match = re.search('Merge pull request #([0-9]+)',l_summary)
        if num_match:
            pr_number = int(num_match.group(1))
            pull_data = i_repo.get_pull(pr_number)
            cq_matches = re.findall('fixes.+([S|F]W[0-9]+).*',pull_data.body,flags=re.I)

            if cq_matches:
                for cq in cq_matches:
                    link='[{}](https://w3.rchland.ibm.com/projects/bestquest/?defect={})'.format(cq,cq)
                    l_closed_issues.append(link)
            pull_comments = pull_data.get_issue_comments()
            for comment in pull_comments:
                cq_matches = re.findall('fixes.+([S|F]W[0-9]+).*',comment.body,flags=re.I)

                if cq_matches:
                    for cq in cq_matches:
                        link='[{}](https://w3.rchland.ibm.com/projects/bestquest/?defect={})'.format(cq,cq)
                        l_closed_issues.append(link)
#                release_notes = re.search('Release note[: ]+(*)',comment.body,flags=re.I)
#                print release_notes

        
    elif 'github.com' in  i_commit.commit.url:
                logging.info("processing github.com")
                logging.info(l_summary)
                pr_list = requests.get(pr_url, 
                headers=config.auth_headers).json()
                logging.debug(json.dumps(pr_list,indent=4))
                logging.debug('length:{}'.format(len(pr_list)))
                for pr_data in pr_list:
                    if pr_data['number']:
                        logging.info(pr_data['number'])
                        pull_data = i_repo.get_pull(pr_data['number'])
                        pull_comments = pull_data.get_issue_comments()
                        for comment in pull_comments:
                            cq_matches = re.findall('fixes.+([S|F]W[0-9]+).*',comment.body,flags=re.I)
                            if cq_matches:
                                for cq in cq_matches:
                                    link='[{}](https://w3.rchland.ibm.com/projects/bestquest/?defect={})'.format(cq,cq)
                                    l_closed_issues.append(link)



                
    print l_notes
    l_closed_issues = list(dict.fromkeys(l_closed_issues))
    l_notes = list(dict.fromkeys(l_notes))

    return l_closed_issues, l_notes



def list_of_pull_requests(i_repo):
    
    pull_dict = dict()

    pulls = i_repo.get_pulls(state='closed', sort='updated' ,direction='desc')

    for pr in pulls:     
        logging.info(pr.number)

        comments = pr.get_issue_comments()

        for comment in comments:
            logging.info(comment.body)

        

        logging.info('commits:{}'.format(pr.commits))
        commits = pr.get_commits()
        for commit in commits:
            logging.info(commit.sha)
            logging.info(commit.commit.message)


        dCTM = datetime.now() - pr.updated_at

        if dCTM > timedelta(days=1):
            logging.info("delta time works")
            break
        


def git_clone(repo_name, url):
    git_args = ['git', 'clone', url, repo_name]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if 'fatal' in  stdoutput:
        print('fatal git_clone')

def git_fetch(_cwd):
    saved_cwd = os.getcwd()
    global workspace_dir
    os.chdir(workspace_dir)
    os.chdir(_cwd)

    git_args = ['git', 'fetch', '--all']

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if 'fatal' in  stdoutput:
        print('fatal git_fetch')
    os.chdir(saved_cwd)

def git_reset(_cwd):
    saved_cwd = os.getcwd()
    global workspace_dir
    os.chdir(workspace_dir)
    os.chdir(_cwd)
    git_args = ['git', 'reset', '--hard', 'FETCH_HEAD']

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if 'fatal' in  stdoutput:
        print('fatal git_reset')
    os.chdir(saved_cwd)



def git_branch(_cwd):
    saved_cwd = os.getcwd()
    global workspace_dir
    os.chdir(workspace_dir)
    os.chdir(_cwd)

    git_args = ['git', 'branch' ]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()

    if 'fatal' in  stdoutput:
        print('fatal git_branch')
    os.chdir(saved_cwd)

    branch = stdoutput.split('*')[1]
    branch = branch.split()[0]

    return branch.strip()

def is_sha_commit(sha_value, _cwd):
    saved_cwd = os.getcwd()
    global workspace_dir
    os.chdir(workspace_dir)
    os.chdir(_cwd)
    git_args = ['git', 'cat-file', '-t', sha_value ]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()

    os.chdir(saved_cwd)

    return('commit' in stdoutput)


def switch_branch(branch_name, _cwd):
    saved_cwd = os.getcwd()
    global workspace_dir
    os.chdir(workspace_dir)
    os.chdir(_cwd)

    git_args = ['git', 'checkout', branch_name]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()

    if 'fatal' in  stdoutput:
        print('fatal switch_branch')
    os.chdir(saved_cwd)


def git_clone_or_reset(repo_name, url, args):
    #Only clone in workspace
    global workspace_dir
    os.chdir(workspace_dir)

    if not os.path.exists(repo_name):
        log('cloning into {}...'.format(repo_name), args)
        git_clone(repo_name, url)
        print 'clone worked:{}'.format(os.path.exists(repo_name))
    else:
        log('{} exists, updating...'.format(repo_name), args)
        git_fetch(_cwd=repo_name)
        git_reset(_cwd=repo_name)



def generate_commit_reports(i_repo_uri, i_begin_commit,
                            i_end_commit):
    # Get the repo that the user requested
    
    l_reports = []
    commit_dict = dict()
    commit_msg_dict = dict()

    l_repo = get_repo(i_repo_uri)
    if l_repo == None:
        return l_reports

    logging.info("id: " + str(l_repo.id))
    logging.info('_repo_uri:{}'.format(i_repo_uri))


    l_commits = l_repo.compare(i_begin_commit, i_end_commit).commits


    # Go through all commits check for duplicates by using commit message which includes author, date, Change-Id

    for l_commit in l_commits:
        logging.info(l_commit)
        
        l_author = l_commit.commit.author
        
        commit_dict.setdefault(l_author.name.encode('ascii','ignore'), []).append(l_commit.commit.message)   
        commit_msg_dict.setdefault(l_commit.commit.message.encode('ascii','ignore'), []).append(l_commit.sha)


    for l_commit in l_commits:

        

        # if the sha does match the last one in the key list it's a duplicate so continue to the next commit. 
        if ((commit_msg_dict[l_commit.commit.message.encode('ascii','ignore')][-1]) != l_commit.sha):
            continue


        logging.info(l_commit.sha)

        # Get the insertion and deletion line counts
        l_insertions = l_commit.stats.additions
        l_deletions = l_commit.stats.deletions
        l_author = l_commit.commit.author
        l_summary = (l_commit.commit.message).split('\n')[0]

        logging.debug(l_insertions) 
        logging.debug(l_deletions)
        logging.debug(l_author.name) 
        logging.debug(l_summary)

        l_closed_issues, l_notes = get_closed_issues(l_repo, l_commit)

        l_report = CommitReport(
            i_repo_uri,
            i_repo_uri.split('/')[-1].replace('.git', ''),
            str(l_commit.sha),
            to_prefix_name_rev(l_commit.sha),
            l_author.name,
            l_summary,
            l_insertions,
            l_deletions,
            l_closed_issues,
            l_notes)
            
            
        if  "Merge pull request" in l_summary:
            # Put the report on the end of the list
            l_reports.append(l_report)
            # don't process merge pull request it creates duplicates 
            continue

        # Search the files for any bumps of submodule versions
        l_files = l_commit.files
        for l_file in l_files:
            # If we have two files to compare with diff...
            if l_file.patch:
                # ... get info about the change, log it...
                l_subrepo_uri, l_subrepo_new_hash, l_subrepo_old_hash \
                    = get_bump_info(l_file, l_repo)

                logging.debug('Found patch...')
                logging.debug('  Subrepo URI: ' + str(l_subrepo_uri))
                logging.debug('  Subrepo new hash: '
                              + str(l_subrepo_new_hash))
                logging.debug('  Subrepo old hash: '
                              + str(l_subrepo_old_hash))
                logging.debug('  Found in: ' + l_file.filename)
                
                if l_subrepo_new_hash \
                        and l_subrepo_old_hash \
                        and l_subrepo_uri \
                        and l_subrepo_uri.startswith('git'):
                    logging.debug('  Bumped')
                    l_subrepo_path = l_subrepo_uri.split('/')[-1]
                    l_subreports = generate_commit_reports(
                    l_subrepo_uri,
                        l_subrepo_old_hash,
                        l_subrepo_new_hash)
                    l_report.subreports.extend(l_subreports)

        # Put the report on the end of the list
        l_reports.append(l_report)


    return l_reports



def parse_arguments(i_args):

    app_description = '''Create Release Note  '''

    l_parser = argparse.ArgumentParser(description=app_description)

    l_parser.add_argument(
        '-dr', '--dry-run', dest='dry_run', action='store_true',
        help='perform a dry run only')

    l_parser.add_argument(
        '-d', '--debug',
        help="Print lots of debugging statements",
        action="store_const", dest="loglevel", const=logging.DEBUG,
        default=logging.WARNING,)

    l_parser.add_argument(
        '-v', '--verbose',
        help="Be verbose",
        action="store_const", dest="loglevel", const=logging.INFO,)
    l_parser.add_argument(
        '-R', '--repo_uri',
        default='github.ibm.com/openbmc/openbmc',
        help='The URI of the repo to get commit information ' \
             +'github.ibm.com/openbmc/openbmc for GHE ' \
             +'github.com/openbmc/openbmc for master')
    l_parser.add_argument(
        '-B', '--branch',
        default='1020-ghe',
        help='branch of repo to get commit information ')
    l_parser.add_argument(
        'earliest_commit',
        help='A reference to the earliest commit to get information for')

    l_parser.add_argument(
        'latest_commit',
        help='A reference (branch name, HEAD, SHA, etc.) to the most ' \
             +'recent commit to get information for')

    l_parser.add_argument(
        '--html_file',
        default=None,
        help='If set to a file path, this script will write an HTML ' \
             +'version of the console output to the file path given')
    l_parser.add_argument(
        '--wiki',
        default=None,
        help='If set to a file path, this script will write an wiki ' \
             +'markdown version of the console to the file path given')

    return l_parser.parse_args(i_args)





def main(i_args):
    # Parse the arguments
    l_args = parse_arguments(i_args)
    logging.basicConfig(level=l_args.loglevel)

    if l_args.dry_run:
        if logging.DEBUG != logging.root.level:
            logging.getLogger().setLevel(level=logging.INFO)
        logging.info('This is a dry run')
        
#    logging.debug('This is a debug message')
#    logging.info('This is an info message')
#    logging.warning('This is a warning message')
#    logging.error('This is an error message')
#    logging.critical('This is a critical message')


    # Generate the commit reports
    l_reports = generate_commit_reports(
        l_args.repo_uri,
        l_args.earliest_commit, 
        l_args.latest_commit)



    l_issues = []
    l_notes = []
    for l_report in l_reports:
        l_issues.extend(l_report.get_all_closed_issues())
        l_notes.extend(l_report.get_all_notes())

    
    l_issues = list(dict.fromkeys(l_issues))
    l_notes = list(dict.fromkeys(l_notes))


  
    # Print commit information to the console
    print '## %s' %  (l_args.latest_commit)
    print 'from %s to %s' % (l_args.earliest_commit,l_args. latest_commit)


    if len(l_issues):
        print 'Fixes:'
        for l_issue in l_issues:
            print '* %s' % (l_issue)
        print '---'

    if len(l_notes):
        print 'Release Notes:'
        for l_note in l_notes:
            if l_note:
                print '* %s' % (l_note)

    print 'Commits...'
    for l_report in l_reports:
        print l_report.to_cl_string()

    # Write to the wiki file if the user set the flag
    if l_args.wiki:
        print 'Writing to Wiki file...'
        l_wiki_file = open(l_args.wiki, 'w+')
        header='## %s \n' % (l_args.latest_commit)
        header += "from %s to %s\n" % (l_args.earliest_commit,l_args. latest_commit)
        l_wiki_file.write(header)
        if len(l_issues):
            l_wiki_file.write('\nFixes:\n')

            for l_issue in l_issues:
                l_wiki_file.write('* %s\n' % (l_issue))
            l_wiki_file.write('\n---')

        if len(l_notes):
            l_wiki_file.write('\nRelease Notes:\n')
            for l_note in l_notes:
                if l_note:
                    l_wiki_file.write('* %s\n' % (l_note))

        
        l_wiki_file.write("\n```\n")
        l_wiki_file.write('Commits...\n')


        for l_report in l_reports:
            l_wiki_file.write('%s\n' % l_report.to_string())
 
        l_wiki_file.write("```\n")

        l_wiki_file.close()
   
    # Write to the HTML file if the user set the flag
    if l_args.html_file:
        print 'Writing to HTML file...'
        l_html_file = open(l_args.html_file, 'w+')
        l_html_file.write('<html><body>\n')
        for l_report in l_reports:
            l_html_file.write(l_report.to_html())
#        l_html_file.write('<p>' + str(l_total_insertions) \
#                          + ' insertions and ' + str(l_total_deletions) \
#                          + ' deletions</p>')
        l_html_file.write('<div>Closed Issues</div>')
        for l_issue in l_issues:
            link = ''
            if l_issue[2]:
                print l_issue[2]
                l_link = "https://w3.rchland.ibm.com/projects/bestquest/?defect=%s" % l_issue[2]
                l_html_file.write('<div><a href='+ l_link \
                    +'href="http://www.github.com/' \
                    + re.sub('#', '/issues/', l_issue[0]) \
                    + '" target="_blank">' + l_issue[0] + '</a> ' \
                    + l_issue[1] + '</div>')

            else:
                l_html_file.write('<div><a href="http://www.github.com/' \
                              + re.sub('#', '/issues/', l_issue[0]) \
                              + '" target="_blank">' + l_issue[0] + '</a> ' \
                              + l_issue[1] + '</div>')
        l_html_file.write('</body></html>')
        l_html_file.close()

if __name__ == '__main__':
    main(sys.argv[1:])
