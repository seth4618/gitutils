#!/home/seth/.virtualenvs/gitutils/bin/python

# https://pygithub.readthedocs.io/en/latest/introduction.html

from github import Github, NamedUser
import os
import sys
from datetime import datetime, timedelta
import pytz
from tzlocal import get_localzone 
import argparser
from pprint import pprint
import webbrowser


parser = argparser.ArgumentParser(description="show activity on an org since a given date")
parser.add_argument('-s', '--since', default="", help='starting date')
parser.add_argument('-d', '--details', action="store_true", help='show details')
parser.add_argument('-l', '--showlinks', action="store_true", help='show links')
parser.add_argument('-w', '--openweb', action="store_true", help='open web page for the PR')
parser.add_argument('-c', '--showcommits', action="store_true", help='show commits')
parser.add_argument('-o', '--org', default='monatized', help='organization to show changes on')
parser.add_argument('-r', '--repo', default=None, help='restrict to this repo only')
parser.add_argument('-i', '--showissues', action="store_true", help='show issues')
parser.add_argument('-p', '--days', type=int, default=1, help='how many days back to go')
parser.add_argument('-m', '--minutes', type=int, default=-1, help='how many minutes to go back (-1 to ignore)')
parser.add_argument('-a', '--afterme', action="store_true", help='do not include PRs where my activity was last')
args = parser.parse_args()
since = None
if args.since != "":
    if len(args.since) > 5:
        since = datetime.strptime(args.since, '%m/%d/%y')
    else:
        since = datetime.strptime(args.since+"/23", '%m/%d/%y')
else:
    since = datetime.today() - timedelta(days=args.days)
if args.minutes != -1:
    since = since - timedelta(minutes=args.minutes)

# convert to UTC, since all github info is in UTC
localTZ = get_localzone()
difference2utc = localTZ.utcoffset(datetime.today())
since = since - difference2utc

details = args.details
showcommits = args.showcommits
showissues = args.showissues
showlinks = args.showlinks
orgname = args.org
reponame = args.repo
afterme = args.afterme
openweb = args.openweb

################################################################
# class to track printing and enable display if dates are right

class MaybePrint:
    ensureUserIsLast = False
    
    def __init__(self):
        self.user = 'Seth'
        self.userLast = datetime(1990, 1, 1)
        self.otherLast = datetime(1990, 1, 1)
        self.lines = []

    def maybePrint(self):
        # print(f"=========== seth:{self.userLast} Other:{self.otherLast}")
        if (self.userLast < self.otherLast) or (not MaybePrint.ensureUserIsLast):
            entire = "\n".join(self.lines)
            print(f"* {entire}")
        else:
            print(f"- {self.lines[0]}")

    def print(self, msg):
        self.lines.append(msg)

    def checkActivity(self, user, date):
        if user == self.user:
            if date > self.userLast:
                self.userLast = date
        else:
            if date > self.otherLast:
                self.otherLast = date

if afterme:
    MaybePrint.ensureUserIsLast = True

################################################################
# helper functions

usermap = {
    'EC2 Default User': 'FromEC2',
    'seth4618': 'Seth',
    'Gabriel Hall': 'Gabe',
    'Adrastopoulos': 'Gabe',
    'Seth': 'Seth',
    'gxlin2': 'Grace',
    'kimjanise': 'Janise'
}

def nicename(name, login):
    if isinstance(name, NamedUser.NamedUser):
        name = name.name
    if name in usermap:
        return usermap[name]
    if login in usermap:
        return usermap[login]
    if login is not None:
        return name
    return f"{name}/{login}"

def getFromEnv(name: str) -> str:
    val = os.getenv(name)
    assert val is not None, "{} must be defined in environment to run this application".format(name)
    return val


# show a PullRequestPart
def showpart(x):
    print(x.label, x.ref, x.sha, x.user)


def bname(label):
    x = label.split(':')
    return x[1]


def brief(body):
    body = body.replace('\n', '|').replace('\r', '')
    if len(body) < 40:
        return body
    return body[0:40]+"..."

################################################################
# main entry

accessToken = getFromEnv('GITHUBPAT')

# using an access token
gh = Github(accessToken)
org = gh.get_organization(orgname)
browserOpened = 1               # if opening web pages, 1 means new window, 2 means new tab in last window

if False:
    repos = org.get_repos()
    for repo in repos:
        print("Repo: {}".format(repo.name))

if showissues:
    print("Issues Changed since {}".format(since))
    issues = org.get_issues(since=since)
    for issue in issues:
        print("Issue:\t{} on {} update:{}".format(issue.title, issue.repository.name, issue.updated_at))
        if showlinks:
            print("\tlink:{}".format(issue.html_url))
        sepr = "\t"
        for assignee in issue.assignees:
            sys.stdout.write("{}{}".format(sepr, nicename(assignee.name, assignee.login)))
            sepr = ", "
        sys.stdout.write("\n")
        for label in issue.get_labels():
            print("\t{}".format(label.name))

repos = org.get_repos()
for repo in repos:
    if reponame is not None and reponame != repo.name:
        continue
    if showcommits:
        for commit in repo.get_commits(since=since):
            author = "?" if commit.author is None else commit.author.login
            if author == "?":
                author = commit.commit.author.name
            print("Commit\t{:10}\t{:7}\t{}\n\t{}".format(repo.name, nicename(author, None), commit.commit.author.date,
                                                         commit.commit.message.replace("\n", "\n\t")))
            for file in commit.files:
                print("\t\t\t+{} -{}\t{}".format(file.additions, file.deletions, file.filename))
            
    for pr in repo.get_pulls():
        if pr.updated_at >= since:
            doprint = False if afterme else True
            pout = MaybePrint()
            user = pr.user
            pout.print("PR {}:{:16} {} {:6} {:4} '{}' by {}".format(repo.name, bname(pr.head.label), pr.updated_at, pr.mergeable_state, pr.state, 
                                                            pr.title, nicename(user.name, user.login)))
            if showlinks:
                pout.print("\tlink:{}".format(pr.html_url))
            if openweb:
                # open in new window first time, then in new tab for each other time
                webbrowser.open(pr.html_url, new=browserOpened)
                browserOpened = 2

            if details:
                pout.print("\tcomments:{}, commits:{}, +{} -{}".format(pr.comments, pr.commits, pr.additions, pr.deletions))
                reviews = pr.get_comments()
                for comment in reviews:
                    if comment.created_at >= since:
                        nn = nicename(comment.user, None)
                        pout.checkActivity(nn, comment.created_at)
                        pout.print("\tRC:{} {}\n\t{}".format(comment.created_at, nn, comment.body.replace('\n', '\n\t')))
                comments = pr.get_issue_comments()
                for comment in comments:
                    if comment.created_at >= since:
                        nn = nicename(comment.user, None)
                        pout.checkActivity(nn, comment.created_at)
                        pout.print("\tIC:{} {}\n\t{}".format(comment.created_at, nicename(comment.user, None), comment.body.replace('\n', '\n\t')))
                commits = pr.get_commits()
                sfiles = {}
                for commit in commits:
                    if commit.commit.author.date >= since:
                        author = "?" if commit.author is None else commit.author.login
                        if author == "?":
                            author = commit.commit.author.name
                        nn = nicename(author, None)
                        pout.checkActivity(nn, commit.commit.author.date)
                        pout.print("\tCommit\t{:7}\t{}\n\t{}".format(nn, commit.commit.author.date,
                                                                 commit.commit.message.replace("\n", "\n\t")))
                        for file in commit.files:
                            pout.print("\t\t+{} -{}\t{}".format(file.additions, file.deletions, file.filename))
                            sfiles[file] = 1
            else:
                comments = pr.get_issue_comments()
                for comment in comments:
                    if comment.created_at >= since:
                        nn = nicename(comment.user, None)
                        pout.checkActivity(nn, comment.created_at)
                        pout.print("\tIC\t{:7}\t{}\t{}".format(nicename(comment.user, None), comment.created_at, brief(comment.body)))
                comments = pr.get_comments()
                for comment in comments:
                    if comment.created_at >= since:
                        nn = nicename(comment.user, None)
                        pout.checkActivity(nn, comment.created_at)
                        pout.print("\tRC\t{:7}\t{}\t{}".format(nicename(comment.user, None), comment.created_at, brief(comment.body)))
                sfiles = {}
                commits = pr.get_commits()
                for commit in commits:
                    if commit.commit.author.date >= since:
                        for file in commit.files:
                            sfiles[file.filename] = 1
                        author = "?" if commit.author is None else commit.author.login
                        if author == "?":
                            author = commit.commit.author.name
                        nn = nicename(author, None)
                        pout.checkActivity(nn, commit.commit.author.date)
                        pout.print("\tCommit\t{:7}\t{}\t{}\t{}".format(nn, commit.commit.author.date, 
                                                                   len(sfiles.keys()), brief(commit.commit.message)))
            pout.maybePrint()
