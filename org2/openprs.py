#!/home/seth/.virtualenvs/gitutils/bin/python

# open all PRs in an org on a repo within a time frame

import webbrowser
from github import Github, NamedUser
import os
import sys
from datetime import datetime, timedelta
import pytz
from tzlocal import get_localzone 
import argparser

parser = argparser.ArgumentParser(description="show PRs in web")
parser.add_argument('-s', '--since', default="", help='starting date')
parser.add_argument('-o', '--org', default='monatized', help='organization to show changes on')
parser.add_argument('-r', '--repo', default=None, help='restrict to this repo only')
parser.add_argument('-c', '--closed', action="store_true", help='report on closed PRs')
parser.add_argument('-a', '--all', action="store_true", help='report on ALL PRs')
parser.add_argument('--noweb', action="store_true", help='do not open web page')
parser.add_argument('-p', '--days', type=int, default=1, help='how many days back to go')
parser.add_argument('-m', '--minutes', type=int, default=-1, help='how many minutes to go back (-1 to ignore)')
args = parser.parse_args()

# deal with how far back we go
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
localTZ = get_localzone()		# convert to UTC, since all github info is in UTC
difference2utc = localTZ.utcoffset(datetime.today())
since = since - difference2utc
status = "closed" if args.closed else ("all" if args.all else "open")
openweb = False if args.noweb else True

# rest of arguments
orgname = args.org
reponame = args.repo

def bname(label):
    x = label.split(':')
    return x[1]

def getFromEnv(name: str) -> str:
    val = os.getenv(name)
    assert val is not None, "{} must be defined in environment to run this application".format(name)
    return val

################################################################
# main entry

accessToken = getFromEnv('GITHUBPAT')

# using an access token
gh = Github(accessToken)
org = gh.get_organization(orgname)

browserOpened = 1

repos = org.get_repos()
for repo in repos:
    if reponame is not None and reponame != repo.name:
        continue

    for pr in repo.get_pulls(state=status, sort="updated", direction="desc"):
        if pr.updated_at >= since:
            user = pr.user
            print("PR {}:{:16} {} {:6} {:4} '{}'".format(repo.name, bname(pr.head.label), pr.updated_at, pr.mergeable_state, pr.state, 
                                                         pr.title))
            # open in new window first time, then in new tab for each other time
            if openweb:
                webbrowser.open(pr.html_url, new=browserOpened)
                browserOpened = 2
            else:
                print(f"   {pr.html_url}")
        else:
            # we are now older than we required, so we can abort
            break

