#!/usr/bin/python3

##
# Copyright c 2016 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##

###############################################################################
# @file commit-tracker
# @brief Prints out all commits on the master branch of the specified
#        repository, as well as all commits on linked submodule
#        repositories
###############################################################################

import argparse
#import git
import config
import json
import logging
import os
import re
import requests
import sys
import time
from github import Github
#GITHUB_AUTH = (config.GITHUB_USER,config.py_token)
GITHUB_AUTH = (config.GITHUB_USER, config.GITHUB_PASSWORD)

class CommitReportEncoder(json.JSONEncoder):
    def default(self, i_obj):
        return i_obj.__dict__

###############################################################################
# @class CommitReport
# @brief A class representing information about a commit and all commits in
#        relevant subrepos
###############################################################################
class CommitReport:
    def __init__(self, i_repo_uri, i_repo_name,  i_sha, i_nice_name,
                 i_summary, i_insertions, i_deletions, i_closed_issues):
        self.repo_uri = i_repo_uri
        self.repo_name = i_repo_name
        self.sha = i_sha
        self.nice_name = i_nice_name
        self.summary = i_summary
        self.insertions = i_insertions
        self.deletions = i_deletions
        self.closed_issues = i_closed_issues
        self.subreports = []

    def to_cl_string(self, i_level=0):
        # Define colors for the console
        RED = '\033[31m'
        BLUE = '\033[94m'
        ENDC = '\033[0m'
        # Put the string together
        l_cl_string = ('  ' * i_level) + RED + self.repo_name + ENDC  + ' ' \
            + BLUE + self.nice_name + ENDC + ' ' \
            + re.sub('\s+', ' ', self.summary)
        # Do the same for every subreport
        for l_report in self.subreports:
            l_cl_string += '\n' + l_report.to_cl_string(i_level + 1)
        return l_cl_string

    def to_html(self, i_level=0):
        l_repo_url = re.sub('git://', 'http://', self.repo_uri)
        # Get HTML for this commit
        l_html = \
            '<div style="margin-left: ' + str(i_level * 20) + 'px">' \
            + '<a href="' + l_repo_url + '" target="_blank" ' \
            + 'style="color: red">' + self.repo_name + '</a>&nbsp;' \
            + '<a href="' + l_repo_url + '/commit/' + self.sha \
            + '" target="_blank" style="color: blue">' + self.nice_name \
            + '</a>&nbsp;' \
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

###############################################################################
# @brief Main function for the script
#
# @param i_args : Command line arguments
###############################################################################
def main(i_args):
    # Parse the arguments
    l_args = parse_arguments(i_args)

    # Set the logger level
    logging.basicConfig(level=logging.ERROR)
#    logging.basicConfig(level=logging.DEBUG)

    # Generate the commit reports
    l_reports = generate_commit_reports(
        l_args.repo_uri,
#        l_args.repo_dir,
        l_args.latest_commit,
        l_args.earliest_commit)

    # Compile issues, insertions, and deletions
    l_issues = []
    l_total_deletions = 0
    l_total_insertions = 0
    for l_report in l_reports:
        l_total_deletions += l_report.get_total_deletions()
        l_total_insertions += l_report.get_total_insertions()
        l_issues.extend(l_report.get_all_closed_issues())

    # Print commit information to the console
    print('Commits...')
    for l_report in l_reports:
        print(l_report.to_cl_string())
    print('Closed issues...')
    for l_issue in l_issues:
        print('%10s' % (l_issue[2]),)
        print('  ' + str(l_issue[0].encode('utf-8')) + ' ' + str(l_issue[1].encode('utf-8')))
    print('Insertions and deletions...')
    print(str(l_total_insertions) + ' insertions')
    print(str(l_total_deletions) + ' deletions')

    # Write to the HTML file if the user set the flag
    if l_args.html_file:
        print('Writing to HTML file...')
        l_html_file = open(l_args.html_file, 'w+')
        l_html_file.write('<html><body>\n')
        for l_report in l_reports:
            l_html_file.write(l_report.to_html())
        l_html_file.write('<p>' + str(l_total_insertions) \
                          + ' insertions and ' + str(l_total_deletions) \
                          + ' deletions</p>')
        l_html_file.write('<div>Closed Issues</div>')
        for l_issue in l_issues:
            link = ''
            if l_issue[2]:
                print(l_issue[2])
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

    # Write to the JSON file if the user set the flag
    if l_args.json_file:
        print('Writing to JSON file...')
        l_json_file = open(l_args.json_file, 'w+')
        l_json_file.write(CommitReportEncoder().encode(l_reports))
        l_json_file.close()

###############################################################################
# @brief Parses the arguments from the command line
#
# @param i_args : The list of arguments from the command line, excluding the
#                 name of the script
#
# @return An object representin the parsed arguments
###############################################################################
def parse_arguments(i_args):
    l_parser = argparse.ArgumentParser(
        description='Prints commit information from the given repo and all ' \
                    +'sub-repos specified with SRC_REV, starting from the ' \
                    +'most recent commit specified going back to the ' \
                    +'earliest commit specified.')
    l_parser.add_argument(
        'repo_uri',
        help='The URI of the repo to get commit information ' \
             +'github.ibm.com/openbmc/openbmc for GHE ' \
             +'github.com/openbmc/openbmc for master')
#    l_parser.add_argument(
#        'repo_dir',
#        help='The directory of the repo to get commit information for')
    l_parser.add_argument(
        'latest_commit',
        help='A reference (branch name, HEAD, SHA, etc.) to the most ' \
             +'recent commit to get information for')
    l_parser.add_argument(
        'earliest_commit',
        help='A reference to the earliest commit to get information for')
    l_parser.add_argument(
        '--html_file',
        default=None,
        help='If set to a file path, this script will write an HTML ' \
             +'version of the console output to the file path given')
    l_parser.add_argument(
        '--json_file',
        default=None,
        help='If set to a file path, this script will write a JSON version ' \
            +'of the generated report to the file path given')
    l_parser.add_argument(
        '--branch',
        default='master',
        help='select branch master, OP920.10 ')
    return l_parser.parse_args(i_args)

###############################################################################
# @brief Generates a list of CommitReport objects, each one
#        representing a commit in the given repo URI and path,
#        starting at the beginning commit inclusive, ending at the
#        end commit exclusive
#
# @param i_repo_uri     : The URI to the repo to get reports for
# @rf remove # @param i_repo_path    : The path to the repo to get reports for
# @param i_begin_commit : A reference to the most recent commit. The
#                         most recent commit to get a report for
# @param i_end_commit   : A reference to the commit farthest in the
#                         past. The next youngest commit will be
#                         the last one to get a report for
#
# @return A list of CommitReport objects in order from newest to
#         oldest commit
###############################################################################
def generate_commit_reports(i_repo_uri, i_begin_commit,
                            i_end_commit):

    # Get the repo that the user requested
    l_repo = get_repo(i_repo_uri)
    print("id: " + str(l_repo.id))
    l_reports = []
    try:
        
        l_commits = l_repo.compare(i_begin_commit, i_end_commit).commits

        # Go through each commit, generating a report
        for l_commit in l_commits:
            # Get the insertion and deletion line counts
            l_insertions = l_commit.stats.additions
            l_deletions = l_commit.stats.deletions
            l_author = l_commit.commit.author
            l_summary = l_author.name + " " + (l_commit.commit.message).split('\n')[0]
            if  "Merge pull request" in l_summary:
                continue

            l_report = CommitReport(
                i_repo_uri,
                i_repo_uri.split('/')[-1].replace('.git', ''),
                str(l_commit.sha),
                to_prefix_name_rev(l_commit.sha),
                l_summary,
                l_insertions,
                l_deletions,
                get_closed_issues(l_commit))
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
                    
#                    print('Found patch...')
#                    print('  Subrepo URI: ' + str(l_subrepo_uri))
#                    print('  Subrepo new hash: '
#                                  + str(l_subrepo_new_hash))
#                    print('  Subrepo old hash: '
#                                  + str(l_subrepo_old_hash))
#                    print('  Found in: ' + l_file.filename)

                    # ... and print the commits for the subrepo if this was a
                    #     version bump
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
    except:
        print("exception in generate_commit_reports: do nothing")
    return l_reports

###############################################################################
# @brief Gets the repo URI, the updated SHA, and the old SHA from a
#        given repo, commit SHA and file
# 
# @param i_repo      : The Repo object to get version bump information
#                      from
# @param i_hexsha    : The hex hash for the commit to search for
#                      version bumps
# @param i_repo_path : The path to the repo containing the file to
#                      get bump information from
# @param i_file      : The path, starting at the base of the repo,
#                      to the file to get bump information from
#
# @return Returns the repo URI, the updatedS SHA, and the old SHA in
#         a tuple in that order
###############################################################################
def get_bump_info(i_file, i_repo):
    # Get the diff text
#    print "File: " + i_file.filename
#    print "Diff Text: " + i_file.patch
#    print "contents_url:" + i_file.contents_url


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

#    print "i_uri",
#    print i_uri
    l_uri = i_uri.strip()
    l_values = l_uri.split('/')

#    if len(l_list) != 3:
#        print "Error wrong uri format. Exiting"
#        for l_out in l_list:
#            print "%s" % l_out.strip()
#        sys.exit()
    count = 0;
    for l_value in l_values:
        if 'github.ibm.com' in l_value:
#            print "Found GHE"
#            print list(l_values)
            l_repo_name = l_values[count+1] + "/" + rchop(l_values[count+2],'.git')
#            print l_repo_name
            l_github = Github(login_or_token = config.py_ibm_token, base_url='https://github.ibm.com/api/v3')
            l_repo = l_github.get_repo(l_repo_name)
#            print list(l_repo.get_branches())
#            print l_repo.default_branch
#            l_repo.edit(default_branch="master")
#            print l_repo.master_branch

        
        elif 'github.com' in l_value:
#            print "Found Master"
            l_repo_name = l_values[count+1] + "/" + l_values[count+2] #@rf
            l_repo_name = rreplace(l_repo_name, ".git", '', 1)
            print(l_repo_name)
            l_github = Github(login_or_token = config.py_token)
            l_repo = l_github.get_repo(l_repo_name)
        count += 1

#    else:
#        print "Error found %s. Unknown uri name" % l_list[0]
#        sys.exit()

    return l_repo



###############################################################################
# @brief Gets the number of changed lines between two commits
#
# @param i_repo         : The Repo object these commits are in
# @param i_begin_commit : A git reference to the beginning commit
# @param i_end_commit   : A git reference to the end commit
#
# @return A two-tuple containing the number of insertions and the number of
#         deletions between the begin and end commit
###############################################################################
def get_line_count(i_repo, i_begin_commit, i_end_commit):
    diff_output = i_repo.git.diff(i_end_commit, i_begin_commit, shortstat=True)
    insertions = 0
    deletions = 0
    insertion_match = re.search('([0-9]+) insertion', diff_output)
    deletion_match = re.search('([0-9]+) deletion', diff_output)
    if insertion_match:
        insertions = int(insertion_match.group(1))
    if deletion_match:
        deletions = int(deletion_match.group(1))
    return insertions, deletions

###############################################################################
# @brief Gets closed issues from the commit message
#
# @param i_commit : The commit to get closed issues for
#
# @return A list of tuples, the first element being the ID of the issue, the
#         second being the title from GitHub
###############################################################################
def get_closed_issues(i_commit):
    l_closed_issues = []
    return l_closed_issues
#    print "i_commit.commit.message"
#    print i_commit.commit.message
#    print "~~~~"
    # Set up the regex
    l_close_regex = re.compile(
        '((F|f)ix((es|ed)?)|(C|c)lose((s|d)?)|(R|r)esolve((s|d)?)). ')
#        + '+(?P<issue>[a-zA-Z0-9#]+\/[a-zA-Z0-9#]+)')
    l_matches = l_close_regex.finditer(i_commit.commit.message)
    
#    l_matches = re.findall(r'resolved by.*?/(\d+)', comment['body'],re.IGNORECASE)

    # Loop through all the matches getting each issue name
    for l_match in l_matches:
        print("i_commit.commit.message")
        print(i_commit.commit.message)
        print("~~~~")

        print("l_match.group",)
        print(l_match.group())
        l_issue_id = l_match.group('issue')
        l_issue_title, l_cq_number = get_issue_title(l_issue_id)
        l_closed_issues.append((l_issue_id, l_issue_title, l_cq_number))
        print("found %s" % l_issue_id)

    insensitive = re.compile(re.escape('cherry-pick'), re.I)
    l_pick = insensitive.findall(i_commit.commit.message)
    insensitive = re.compile(re.escape('patch:'), re.I)
    l_patch = insensitive.findall(i_commit.commit.message)

    if l_pick or l_patch:
        match = re.search(r'bug:(.+)',i_commit.commit.message)
        if match:
            type = 'gh'
            bug_number = str(match.group(1)).strip()
            for char in bug_number:
                if char.isalpha():
                    type = 'cq'

            if type == 'cq':
                l_issue_id = ''
                l_issue_title = ''
                l_closed_issues.append((l_issue_id, l_issue_title, bug_number))
            else:
                l_issue_id = 'openbmc/openbmc#' + bug_number
                l_issue_title, l_cq_number = get_issue_title(l_issue_id)
                l_closed_issues.append((l_issue_id, l_issue_title, l_cq_number))


        l_cherry_pick_regex = re.compile(
            '\+((F|f)ix((es|ed)?)|(C|c)lose((s|d)?)|(R|r)esolve((s|d)?)). '
            + '+(?P<issue>[a-zA-Z0-9#]+\/[a-zA-Z0-9#]+)')
        #search files
        l_files = i_commit.files
        for l_file in l_files:
#            print "l_file",
#            print l_file
        # If we have two files to compare with diff...
            if l_file.patch:
#                print l_file.patch
#                for line in l_file.patch.readlines():
#                    print line

                l_matches = l_cherry_pick_regex.finditer(l_file.patch)
                   # Loop through all the matches getting each issue name
                for l_match in l_matches:
#                    print l_match.group()
                    l_issue_id = l_match.group('issue')
                    l_issue_title, l_cq_number = get_issue_title(l_issue_id)
                    l_closed_issues.append((l_issue_id, l_issue_title, l_cq_number))
                    print("cherry-pick or patch found %s" % l_issue_id)

    return l_closed_issues

###############################################################################
# @brief Gets the title of an issue based on the issue ID
#
# @param i_issue_id : The ID of the issue to get the title for
#
# @return The title of the issue
###############################################################################
def get_issue_title(i_issue_id):
    print("i_issue_id:",)
    print(i_issue_id)

    # Construct the URL
    l_url_tail = re.sub('#', '/issues/', i_issue_id)
    l_full_url = 'https://api.github.com/repos/' + l_url_tail
    l_title = ''
    l_cq_number = ''
    print("l_full_url:",)
    print(l_full_url)
    # Send in the web request
    l_response = requests.get(l_full_url, auth=GITHUB_AUTH)
    if 200 == l_response.status_code:
        l_issue = l_response.json()
        l_title = l_issue['title']
        if l_issue['body'] is not None:
            match = re.search(r'<cde:info> (.+) </cde:info>',l_issue['body'])
            if match:
                l_cq_number = match.group(1)

    else:
        logging.error(l_response.text)
        logging.error('Recieved status code ' \
                      + str(l_response.status_code) \
                      + ' when getting issue titles.')
    return l_title, l_cq_number

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

# Only run main if run as a script
if __name__ == '__main__':
    main(sys.argv[1:])

