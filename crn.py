#!/usr/bin/env python3

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

import shlex

sys.path.append("/home/rfrandse/ewm")
import ewm
ewm_instance = ewm.Ewm()



workspace_dir = os.getcwd()


def rchop(thestring, ending):
    if thestring.endswith(ending):
        return thestring[:-len(ending)]
    return thestring

def rreplace(s_value, old, new, occurrence):
    line = s_value.rsplit(old, occurrence)
    return new.join(line)

def subtract_lists(A_list,B_list):
    return [x for x in A_list if x not in B_list]

def intersect_lists(A_list,B_list):
    return list(set(A_list).intersection(B_list))


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
                 i_summary, i_insertions, i_deletions, i_closed_issues, i_notes, i_stgDefects):
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
        self.stgDefects = i_stgDefects
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
    def get_all_stgDefects(self):
        l_stgDefects = self.stgDefects
        for l_commit in self.subreports:
            l_stgDefects.extend(l_commit.get_all_stgDefects())
        return l_stgDefects

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


def find_fixes(i_data):

    l_closed_issues = []
    l_stgDefects = []

    try:
        
        cq_matches = re.findall('fixes.+([S|F]W\d\d\d\d\d\d).*',i_data,flags=re.I)
        if cq_matches:      
            for cq in cq_matches:
                logging.info(cq)
                l_closed_issues.append(cq)
            
        ewm_matches = re.findall('fixes[: ]*(PE\w+)',i_data,flags=re.I)
        if ewm_matches:
            for ewm in ewm_matches:
                logging.info(ewm)
                l_closed_issues.append(ewm)

        stg_matches = re.findall('fixes[: ]*\s+(\d{6,8})',i_data,flags=re.I)
        if stg_matches:
            for stg in stg_matches:
                logging.info(stg)
                l_stgDefects.append(stg)


        url_list = []
        url_list.append('https://jazz07.rchland.ibm.com:13443/jazz/resource/itemName/com.ibm.team.workitem.WorkItem/')
        url_list.append('https://jazz07.rchland.ibm.com:13443'+\
                                '/jazz/web/projects/CSSD#action=com.ibm.team.workitem.viewWorkItem&id=')


        for jazz_url in url_list:
            jazz_url = re.escape(jazz_url)

            regex = 'fixes[: ]*\s+'+ jazz_url +'(\d{6,8})'

            stg_matches = re.findall(regex, i_data, flags=re.I )
            if stg_matches:
                for stg in stg_matches:
                    logging.info(stg)
                    l_stgDefects.append(stg)





        logging.info("List of closed issues and stgDefects")
        logging.info(l_closed_issues)
        logging.info(l_stgDefects)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.warning(exc_type, fname, exc_tb.tb_lineno)


    return l_closed_issues, l_stgDefects

def find_notes(i_data):

    l_notes = []
    
    release_notes = re.search(r'Release note[: ](.*)',i_data,flags=re.I | re.DOTALL)
    if release_notes:
        lines =  release_notes.group(1).splitlines()
        for line in lines:
            if "::" in line:
                note = line.split('::')
#                l_notes.append(note[0].encode("utf8").strip())
                l_notes.append(note[0].strip())

                break
            else:
                #l_notes.append(line.encode("utf8").strip())
                l_notes.append(line.strip())


    return l_notes



def get_closed_issues(i_repo, i_commit):

    l_closed_issues = []
    l_notes = []
    l_stgDefects = []

    try:
        #Get the PR number from the title
        l_summary = ((i_commit.commit.message).split('\n')[0]).strip()   
        logging.info(i_commit.commit.url)
        pr_url = rreplace(i_commit.commit.url, "/git", '', 1)     
        pr_url += "/pulls"
        logging.info("function: get_closed_issues")
        logging.info(pr_url)
        pull_data = None
        
        if 'github.ibm.com' in i_commit.commit.url:
            logging.info("processing github.ibm.com")
            logging.info(l_summary)
            num_match = re.search('\(#([0-9]+)\)$',l_summary)
            if num_match:
                pr_number = int(num_match.group(1))
                try:
                    pull_data = i_repo.get_pull(pr_number)
                except:
                    logging.warning("Unable to process PR:{}".format(pr_number))
                    return l_closed_issues, l_notes
                list1, list2 = find_fixes(pull_data.body)
                l_closed_issues.extend(list1)
                l_stgDefects.extend(list2)
                
                pull_comments = pull_data.get_issue_comments()
                for comment in pull_comments:
    #                print comment.body
                    list1, list2 = find_fixes(comment.body)
                    l_closed_issues.extend(list1)
                    l_stgDefects.extend(list2)
                    l_notes.extend(find_notes(comment.body))

            num_match = re.search('Merge pull request #([0-9]+)',l_summary)
            if num_match:
                pr_number = int(num_match.group(1))
                pull_data = i_repo.get_pull(pr_number)
                list1, list2 = find_fixes(pull_data.body)
                l_closed_issues.extend(list1)
                l_stgDefects.extend(list2)

                pull_comments = pull_data.get_issue_comments()
                for comment in pull_comments:
                    list1, list2 = find_fixes(comment.body)
                    l_closed_issues.extend(list1)
                    l_stgDefects.extend(list2)
                    l_notes.extend(find_notes(comment.body))

            
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
                                list1, list2 = find_fixes(comment.body)
                                l_closed_issues.extend(list1)
                                l_stgDefects.extend(list2)
                                l_notes.extend(find_notes(comment.body))


                    
        print(l_closed_issues)
        print(l_notes)
        print(l_stgDefects)
        l_closed_issues = list(dict.fromkeys(l_closed_issues))
        l_notes = list(dict.fromkeys(l_notes))
        l_stgDefects = list(dict.fromkeys(l_stgDefects))
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.warning(exc_type, fname, exc_tb.tb_lineno)

    return l_closed_issues, l_notes, l_stgDefects



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
        

def git_add(filename):

    git_args = ['git', 'add', filename]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()
    if 'fatal' in  stdoutput:
        print('git_add fatal')

def git_commit(commit_msg):

    git_args = ['git', 'commit', '-m', commit_msg]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()
    if 'fatal' in  stdoutput:
        print('git_commit fatal')

def git_show(sha):
    git_args = ['git', 'show', sha]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()

    if 'fatal' in  stdoutput:
        print(stdoutput)
        print('git_show fatal %s' % sha)
    else:
        print(stdoutput)

def git_log(parms_array):

    git_args = ['git', 'log']+parms_array

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()

    if 'fatal' in  stdoutput:
        print('fatal')
    else:
        return stdoutput

    return []


def git_clone(repo_name, url):
    git_args = ['git', 'clone', url, repo_name]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()
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
    stdoutput=stdoutput.decode()
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
    stdoutput=stdoutput.decode()
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
    stdoutput=stdoutput.decode()
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
    stdoutput=stdoutput.decode()
#    if 'fatal' in  stdoutput:
#        print('fatal')
    os.chdir(saved_cwd)

    return('commit' in stdoutput)


def cq_to_ewm(cq_number):

#    cqcmd.pl -db AIXOS -schema STGC_AIX -cqhost cqweb.rchland.ibm.com  -port 6600 -user fspbld@us.ibm.com -relog -action query -fields "force_Commit::yes~~sql::SELECT 
#    resource_type,resource_name,system_type,system_name,parentdefect,parentdefect.universal_id from ExternalResource 
#    where  parentdefect.universal_id='SW552582' or parentrequirement.universal_id='SW552582'"

    args_str = "cqcmd.pl -db AIXOS -schema STGC_AIX -cqhost cqweb.rchland.ibm.com  -port 6600 -relog -action query  -fields " 
    args_str += "\"force_commit::yes~~sql::SELECT  resource_type,resource_name,system_type,system_name,parentdefect,parentdefect.universal_id from ExternalResource "
    args_str += "where parentdefect.universal_id=\'{}\' or parentrequirement.universal_id=\'{}\'\"".format(cq_number,cq_number)

    cq_args = shlex.split(args_str)
    process = subprocess.Popen(cq_args, stdout=subprocess.PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()

    logging.info(stdoutput)
    lines = stdoutput.splitlines()
    for line in lines:
        # Example lines:
        # defect|1154197|CMVC95|aix@auscmvc.rchland.ibm.com@2035|AIXOS13474966|SW552204
        # STGDefect|313544|EWM|https://jazz07.rchland.ibm.com:13443/jazz/projects/CSSD|AIXOS13474966|SW552204
        defect_info = line.split('|')
        if "STGDefect" in defect_info[0]:
            return defect_info[1].strip()

    return None




def cq_info(cq_number):
    args_str = "cqcmd.pl -db AIXOS -schema STGC_AIX -cqhost cqweb.rchland.ibm.com  -port 6600 -relog -action query  -fields \"force_commit::yes~~sql::SELECT universal_id,headline, Ownerinfo from defect where Universal_id = \'"
    args_str += "{0}\'\"".format(cq_number)
    cq_args = shlex.split(args_str)
    process = subprocess.Popen(cq_args, stdout=subprocess.PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()

    return stdoutput

def read_cq_keywords(cq_number):
    args_str = "/gsa/ausgsa/projects/p/pfd_rat_tools/prod/cqcmd.pl -db AIXOS \
            -schema STGC_AIX -cqhost cqweb.rchland.ibm.com  -port 6600 -relog \
            -action query \
            -fields \"force_commit::yes~~sql::SELECT keywords from defect where Universal_id = \'"
    args_str += "{0}\'\"".format(cq_number)
    cq_args = shlex.split(args_str)


    process = subprocess.Popen(cq_args, stdout=subprocess.PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()

    results = rreplace(stdoutput,'|\n','', 1)

    return results

def write_cq_keywords(cq_number, data):

    args_str = "/gsa/ausgsa/projects/p/pfd_rat_tools/prod/cqcmd.pl -db AIXOS \
        -schema STGC_AIX -cqhost cqweb.rchland.ibm.com  -port 6600 -relog \
        -action modify -univid {0} \
        -fields \"force_commit::yes~~Keywords::{1} \""\
        .format(cq_number, data)

    
    cq_args = shlex.split(args_str)


    process = subprocess.Popen(cq_args, stdout=subprocess.PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()

    return stdoutput

def read_ewm_universalid_summary_owner(ewmId):
    try:
        workItem = ewm_instance.display(ewmId)
        universal_id = workItem["Universal ID"]
        summary =  workItem["Summary"]
        owner = workItem["Owned By"]
        return (universal_id, summary, owner)
    except:
        logging.warning("Unable to read ewm Universal ID and Summary\
                and owner:{}".format(ewmId))



def read_ewm_tags(ewmId):
    try:
        workItem = ewm_instance.display(ewmId)
        return (workItem["Tags"])
    except:
        logging.warning("Unable to read ewm Tags:{}".format(ewmId))


def write_ewm_tags(ewmId, data):
    try:
        ewm_instance.modify(id=ewmId,attributes=["Tags:", data])
    except:
        logging.warning("Unable to write ewm Tags:{}".format(data))

def update_ewm_tags_field(ewmId, data='merged'):

    original_text = read_ewm_tags(ewmId)
    if data in original_text:
        return
    new_text = original_text + " " + data
    print("Writing",ewmId,":",new_text)
    write_ewm_tags(ewmId, new_text)


def read_ewm_priority_justification(ewmId):
    try:
        workItem = ewm_instance.display(ewmId)
        return (workItem["Priority Justification"])
    except:
        logging.warning("Unable to read ewm priority justification:{}".format(ewmId))


def write_ewm_priority_justification(ewmId, data):
    try:
        ewm_instance.modify(id=ewmId,attributes=["Priority Justification:", data])
    except:
        logging.warning("Unable to write ewm priority justification:{}".format(data))

def update_ewm_priority_justification_tag_info(ewmId, tag):
    tag_info = "OPENBMC_TAG:%s" % tag

    original_text = read_ewm_priority_justification(ewmId)
    if tag_info in original_text:
        return
    new_text = tag_info + " " + original_text
    print("Writing",ewmId,":",new_text)
    write_ewm_priority_justification(ewmId, new_text)



def read_cq_priority_justification(cq_number):
    args_str = "/gsa/ausgsa/projects/p/pfd_rat_tools/prod/cqcmd.pl -db AIXOS \
            -schema STGC_AIX -cqhost cqweb.rchland.ibm.com  -port 6600 -relog \
            -action query \
            -fields \"force_commit::yes~~sql::SELECT Priority_Justification, keywords from defect where Universal_id = \'"
    args_str += "{0}\'\"".format(cq_number)
    cq_args = shlex.split(args_str)


    process = subprocess.Popen(cq_args, stdout=subprocess.PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()

    results = rreplace(stdoutput,'|\n','', 1)

    return results

def write_cq_priority_justification(cq_number, data):

    args_str = "/gsa/ausgsa/projects/p/pfd_rat_tools/prod/cqcmd.pl -db AIXOS \
        -schema STGC_AIX -cqhost cqweb.rchland.ibm.com  -port 6600 -relog \
        -action modify -univid {0} \
        -fields \"force_commit::yes~~Priority_Justification::{1} \""\
        .format(cq_number, data)

    
    cq_args = shlex.split(args_str)


    process = subprocess.Popen(cq_args, stdout=subprocess.PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput=stdoutput.decode()

    return stdoutput

def read_cq_notes(cq_number):
    l_tag_list = []
    args_str = "/gsa/ausgsa/projects/p/pfd_rat_tools/prod/cqcmd.pl -db AIXOS \
            -schema STGC_AIX -cqhost cqweb.rchland.ibm.com  -port 6600 -relog \
            -action query  -fields \"force_commit::yes~~sql::SELECT Notes_Log from defect where Universal_id = \'"
    args_str += "{0}\'\"".format(cq_number)
    cq_args = shlex.split(args_str)


    process = subprocess.Popen(cq_args, stdout=subprocess.PIPE)
    stdoutput, stderroutput = process.communicate()
    results=stdoutput.decode()

    return results

def write_cq_note(cq_number, data):

    args_str = "/gsa/ausgsa/projects/p/pfd_rat_tools/prod/cqcmd.pl -db AIXOS \
        -schema STGC_AIX -cqhost cqweb.rchland.ibm.com  -port 6600 -relog \
        -action modify -univid {0} \
        -fields \"force_commit::yes~~Note_Entry::{1} \""\
        .format(cq_number, data)

    
    cq_args = shlex.split(args_str)


    process = subprocess.Popen(cq_args, stdout=subprocess.PIPE)
    stdoutput, stderroutput = process.communicate()
    results=stdoutput.decode()

    return results

def check_for_tag(tag_info, data):
    results = False
    for line in data.splitlines():
        if (tag_info in line):
            results = True
    return results

def update_keywords(cq_number):

    original_text = read_cq_keywords(cq_number)

    matches = re.findall('merged',original_text,flags=re.I)
    if matches:
        return
    new_text = original_text.strip() + "\nMerged"
    write_cq_keywords(cq_number, new_text)


def update_cq_tag_info(cq_number, tag):
    tag_info = "OPENBMC_TAG:%s" % tag
    if not check_for_tag(tag_info, read_cq_notes(cq_number)):
        write_cq_note(cq_number,tag_info)

    original_text = read_cq_priority_justification(cq_number)
    if tag_info in original_text:
        return
    new_text = tag_info + "\n" + original_text
    write_cq_priority_justification(cq_number, new_text)

def switch_branch(branch_name, _cwd):
    saved_cwd = os.getcwd()
    global workspace_dir
    os.chdir(workspace_dir)
    os.chdir(_cwd)

    git_args = ['git', 'checkout', branch_name]

    process = subprocess.Popen(git_args, stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    stdoutput = stdoutput.decode()

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
        print('clone worked:{}'.format(os.path.exists(repo_name)))
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

    try:

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

            l_closed_issues, l_notes, l_stgDefects = get_closed_issues(l_repo, l_commit)

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
                l_notes,
                l_stgDefects)
                
                
            if  "Merge pull request" in l_summary:
                # Put the report on the end of the list
                l_reports.append(l_report)
                # don't process merge pull request it creates duplicates 
                logging.info("found Merge pull request don't process")
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
            logging.info("append l_report")
            l_reports.append(l_report)


    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.warning("exception in generate_commit_reports: do nothing")
        logging.warning(exc_type, fname, exc_tb.tb_lineno)


    return l_reports

def update_release_file(filename, line):
    with open(filename, 'r+') as f:
        content = f.read()
        if line in content:
            return
        f.seek(0, 0)
        f.write(line.rstrip('\r\n') + '\n' + content)



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
        '-t', '--tag_repo_uri',
        default='github.ibm.com/rfrandse/openbmc',
        help='The URI of the repo to get tag commit information ' \
             +'github.ibm.com/rfrandse/openbmc default ')
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
        '--wiki', dest='create_wiki', action='store_true',
        help='If set create release wiki page and update reference ' \
             +'links in various release pages')
    l_parser.add_argument(
        '-D', dest='dir', default=None,
        help='set a dirctory path to write release files ')
    l_parser.add_argument(
        '--gsa', dest='gsa_tag_info', default=None, 
        help='If set this script will write a file <latest_commit>.txt to ' \
             +'/gsa/ausgsa/projects/b/bmctaglists/ ' \
             +'latest_commit option text is tag name  ')
    l_parser.add_argument(
        '-u','--update', dest='update_cq', action='store_true',
        help='If set this script will update priority justifcation ' \
             +'with tag name')
    l_parser.add_argument(
        '-E','--ewm', dest='update_ewm', action='store_true',
        help='If set this script will update priority justifcation ' \
             +'with tag name in ewm ')

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

    l_latest_commit = l_args.latest_commit

    if l_args.gsa_tag_info:
        my_repo = get_repo(l_args.tag_repo_uri)
        l_commit = my_repo.get_commit(l_args.latest_commit)
        # convert to sha value, since tag hasn't been released
        l_latest_commit = l_commit.commit.sha

    
    print(l_args.gsa_tag_info)

#   exit()

    # Generate the commit reports
    l_reports = generate_commit_reports(
        l_args.repo_uri,
        l_args.earliest_commit, 
        l_latest_commit)

    tag_name = None
    release_dir =  os.getcwd()
    l_match = re.search('fw(\d\d\d\d).',l_args.latest_commit)
    if (l_match):
        release_dir = l_match.group(1)
        if l_args.dir:
            release_dir = l_args.dir
        if not os.path.exists(release_dir):
            logging.error("directory {} doesn't exist. Please create".format(release_dir))
            exit()

    if l_args.dir:
        release_dir = l_args.dir
        if not os.path.exists(release_dir):
            logging.error("directory {} doesn't exist. Please create".format(release_dir))
            exit()

    l_issues = []
    l_notes = []
    l_stgDefects = []
    for l_report in l_reports:
        l_issues.extend(l_report.get_all_closed_issues())
        l_notes.extend(l_report.get_all_notes())
        l_stgDefects.extend(l_report.get_all_stgDefects())


    l_issues = list(dict.fromkeys(l_issues))
    print(l_issues)


    try: 
        cq_list = sorted(l_issues, key=lambda x: int("".join([i for i in x if i.isdigit()])))
    except:
        cq_list = l_issues


    # list(dict.fromkeys() removes duplicates. 
    l_notes = list(dict.fromkeys(l_notes))

    l_stgDefects =  list(dict.fromkeys(l_stgDefects))
    l_stgDefects.sort()

    print(l_stgDefects)


    # combined STGDefect and  ClearQuest lists
    if len(cq_list):
        #convert CQ to EWM ids but only the ones we don't have already. 
        ewm_uniId_list = []
        if len(l_stgDefects):
            for ewmId in l_stgDefects:
                uniId, s, o = read_ewm_universalid_summary_owner(ewmId)
                ewm_uniId_list.append(uniId)

        whats_left_list = subtract_lists(cq_list,ewm_uniId_list)
        if len(whats_left_list):
            for cq in whats_left_list:
                print("Processing cq_to_ewm:",cq)
                ewmId = cq_to_ewm(cq)
                if ewmId is None:
                    continue
                print("adding to stgDefects list: ",ewmId)
                l_stgDefects.append(ewmId)

            #get rid of duplictates and sort list
            l_stgDefects =  list(dict.fromkeys(l_stgDefects))
            l_stgDefects.sort()
            print(l_stgDefects)


 


    if l_args.gsa_tag_info:


        prev_txtfile = ''
        if l_args.dry_run:
            p_filename = '%s.txt' % (l_args.earliest_commit)
        else:
            p_filename = '/gsa/ausgsa/projects/b/bmctaglists/%s.txt' % (l_args.earliest_commit) 

        try: 
            with open(p_filename, 'r') as f:
                prev_txtfile = f.read()
                print(prev_txtfile)


                l_prev_stgDefects = []
                l_prev_reports = generate_commit_reports(
                    l_args.repo_uri,
                    l_args.gsa_tag_info,
                    l_args.earliest_commit)

                for l_prev_report in l_prev_reports:
                    l_prev_stgDefects.extend(l_prev_report.get_all_stgDefects())
                
                l_prev_stgDefects =  list(dict.fromkeys(l_prev_stgDefects))
                l_prev_stgDefects.sort()

                for prev_ewmId in l_prev_stgDefects:
                    universalid, summary, owner = read_ewm_universalid_summary_owner(prev_ewmId)
                    print(universalid)
                    if universalid in prev_txtfile:
                        continue
                    print("adding previous defect to stgDefects list: ",prev_ewmId)
                    l_stgDefects.append(prev_ewmId)
                #get rid of duplictates and sort list
                l_stgDefects =  list(dict.fromkeys(l_stgDefects))
                l_stgDefects.sort()
                print("gsa defect list: ", l_stgDefects)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logging.warning("warning with previous defects list:",exc_type, fname, exc_tb.tb_lineno)


        #process STGDefects 
        if len(l_stgDefects):
            if l_args.dry_run:
                filename = '%s.txt' % (l_args.latest_commit)
            else:
                filename = '/gsa/ausgsa/projects/b/bmctaglists/%s.txt' % (l_args.latest_commit) 
            with open(filename, 'w+') as txtfile:
                tmpStr = ""
                for ewmId in l_stgDefects:
                    universalid, summary, owner = read_ewm_universalid_summary_owner(ewmId)
                    #Format of report  
                    #Universal Id|Summary|Owner
                    tmpStr += "{}|{}|{}\n".format(universalid, summary, owner)
                txtfile.write(tmpStr)
            print("\nWriting:", filename)


    if l_args.update_ewm:
        #process STGDefects 
        if len(l_stgDefects):
            for ewmId in l_stgDefects:
                print("updating ewmId:%s with tag info" % (ewmId))
                update_ewm_priority_justification_tag_info(ewmId, l_args.latest_commit)
                update_ewm_tags_field(ewmId)


    # Print commit information to the console
    print('## %s' %  (l_args.latest_commit))
    print('from %s to %s' % (l_args.earliest_commit,l_args. latest_commit))

    if len(l_stgDefects):
        print('Fixes STGDefects:')
        for ewmId in l_stgDefects:
            link='[{}](https://jazz07.rchland.ibm.com:13443/jazz/web/projects/CSSD#action=com.ibm.team.workitem.viewWorkItem&id={}'.format(ewmId,ewmId)
            u, summary, o = read_ewm_universalid_summary_owner(ewmId)
            print('* %s:`%s`' % (link, summary[0:90]))

        print('---')


    if len(l_notes):
        print('Release Notes:')
        for l_note in l_notes:
            if l_note:
                print('* %s' % (l_note))

    print('Commits...')
    for l_report in l_reports:
        print(l_report.to_cl_string())

  
    # Write to the wiki file if the user set the flag
    if l_args.create_wiki:
        release_wiki = release_dir + "/" + l_args.latest_commit + ".md"
        print('Writing to Wiki file...{}'.format(release_wiki))
        with open(release_wiki, 'w+') as l_wiki_file:
            header='## %s \n' % (l_args.latest_commit)
            header += "from %s to %s\n" % (l_args.earliest_commit,l_args. latest_commit)
            l_wiki_file.write(header)

            if len(l_stgDefects):
                l_wiki_file.write('\nFixes STGDefects:\n')
                for ewmId in l_stgDefects:
                    link='[{}](https://jazz07.rchland.ibm.com:13443/jazz/web/projects/CSSD#action=com.ibm.team.workitem.viewWorkItem&id={})'.format(ewmId,ewmId)
                    u, summary, o = read_ewm_universalid_summary_owner(ewmId)
                    l_wiki_file.write('* %s:`%s`\n' % (link, summary[0:90]))

                l_wiki_file.write('\n---')

            if len(l_notes):
                l_wiki_file.write('\nRelease Notes:\n')
                for l_note in l_notes:
                    if l_note:
                        l_wiki_file.write('* %s\n' % (l_note))
            
            l_wiki_file.write("\n```\n")
            l_wiki_file.write('Commits...\n')


            for l_report in l_reports:
                #l_wiki_file.write('%s\n' % l_report.to_string().encode("utf-8"))
                l_wiki_file.write('%s\n' % l_report.to_string())

            l_wiki_file.write("```\n")

        l_match = re.match(r'(fw[0-9].+)-[0-9].*', l_args.latest_commit)
        if l_match:
            release_link_file = l_match.group(1) + ".md"
            if os.path.exists(release_link_file):
                tag = l_args.latest_commit
                c_date = datetime.now().strftime("%Y-%m-%d")
                line = "*   [{}](https://github.ibm.com/openbmc/release-notes/wiki/{})     {}".format(tag,tag,c_date)
                update_release_file(release_link_file, line)
                git_add(release_wiki)
                git_add(release_link_file)
                commit_message = "add {}".format(tag)
                git_commit(commit_message)
                log_sha = git_log(['-n 1', '--pretty=format:%h'])
                git_show(log_sha)

                print('\nif good ---->   git push origin master\n')
                print('https://github.ibm.com/openbmc/openbmc/wiki/Release-Information\n')

            else:
                logging.error("Release link file not found: {}".format(release_link_file))

            
    # Write to the HTML file if the user set the flag
    if l_args.html_file:
        print('Writing to HTML file...')
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

if __name__ == '__main__':
    main(sys.argv[1:])
