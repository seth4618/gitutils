#!/home/seth/.virtualenvs/gitutils/bin/python

from git import Repo
from pprint import pprint
from datetime import datetime
import argparse
import sys

parser = argparse.ArgumentParser(description="Compare the commits starting from LCA of two branches")
parser.add_argument("-r", "--repodir", default="/home/seth/research/pco/wallet", help="base of repo")
parser.add_argument("-s", "--showmsgs", action="store_true", help="show messages as well")
parser.add_argument("aname", nargs=1, help="branch A")
parser.add_argument("bname", nargs=1, help="branch B")
args = parser.parse_args()
aname = args.aname[0]
bname = args.bname[0]
showmsgs = args.showmsgs

repodir = args.repodir
repo = Repo(repodir)
assert not repo.bare

# show untracked files on active branch
if False:
    untracked = repo.untracked_files
    pprint(untracked)

# get all branches  (repo.heads is same)
if False:
    branches = repo.branches
    for branch in branches:
        print("Local: {}".format(branch.name))
    remote_refs = repo.remote().refs
    for refs in remote_refs:
        print("Remote: {}".format(refs.name))


def getHistory(start):
    history = []
    while start is not None:
        history.append(start)
        if len(start.parents) == 0:
            history.reverse()
            return history
        start = start.parents[0]


def getBranch(name):
    branches = repo.branches
    for branch in branches:
        if name == branch.name:
            return branch
    print("Did not find branch: '{}'".format(name))
    return None


def oneLiner(commit):
    sys.stdout.write("{} {} {: <15.15} | ".format(datetime.fromtimestamp(commit.committed_date).strftime("%Y-%m-%d"), commit.hexsha[0:8], commit.author.name))
    for fname in commit.stats.files.keys():
        sys.stdout.write("\t{}".format(fname))
    if showmsgs:
        if len(commit.message) > 0:
            sys.stdout.write("\n\t{}".format(commit.message))
    sys.stdout.write("\n")


def oneLiners(history, branchname):
    print("======== {}".format(branchname))
    for c in history:
        oneLiner(c)


A = getBranch(aname)
Alog = getHistory(A.commit)
maxA = len(Alog)
B = getBranch(bname)
Blog = getHistory(B.commit)
maxB = len(Blog)
print(maxA, maxB)

# find last common ansector
newest = len(Alog) if len(Alog) < len(Blog) else len(Blog)
lastCommon = 0
for i in range(newest):
    # print(Alog[maxA-i], Blog[maxB-i])
    # print(datetime.fromtimestamp(Alog[maxA-i].committed_date).strftime("%Y-%m-%d"), Alog[maxA-i].author, Alog[maxA-i].hexsha, Alog[maxA-i].message)
    if Alog[i] != Blog[i]:
        break
    lastCommon = i
print("Looking in {} between {} and {}".format(repodir, aname, bname))
print("LCA is at {}: {}".format(lastCommon, Alog[lastCommon].hexsha[:8]))
oneLiners(Alog[lastCommon+1:], aname)
oneLiners(Blog[lastCommon+1:], bname)
