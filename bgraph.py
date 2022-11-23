#!/home/seth/.virtualenvs/gitutils/bin/python

from git import Repo
from pprint import pprint
from datetime import datetime
import argparse
import sys

parser = argparse.ArgumentParser(description="show how branches are related")
parser.add_argument("-v", "--verbose", action="store_true", help="be verbose")
parser.add_argument("-R", "--remote", action="store_true", help="include remote branches")
parser.add_argument("-r", "--repodir", default="/home/seth/research/pco/wallet", help="base of repo")
parser.add_argument("branches", nargs='*', help="branches to compare")
args = parser.parse_args()
verbose = args.verbose
includeRemote = args.remote
repodir = args.repodir
branches = args.branches

repo = Repo(repodir)
assert not repo.bare

################################################################
# helper routines


# get all branches.  If remote=true, include remote braches
# return dictionary
def getAllBranches(remote=False):
    result = {}
    for branch in repo.branches:
        result[branch.name] = branch
    if remote:
        for branch in repo.remote().refs:
            result[branch.name] = branch
    return result


class Node:
    # all commits seen so far
    all = {}
    root = None
    
    # create a new node
    def __init__(self, commit, child):
        # print("Adding {} as parent of {}".format(commit, child))
        self.name = None
        self.commit = commit
        self.parent = None
        self.depth = None
        if child is not None:
            self.children = [child]
        else:
            self.children = []
        if self.commit.hexsha in Node.all:
            print("{} is already in dictionary".format(self.getName()))
            raise ValueError('duplicate in hash')
        Node.all[self.commit.hexsha] = self

    def getName(self):
        if self.name is not None:
            return self.name
        return self.commit.hexsha[0:8]

    def __str__(self):
        result = ""
        if self.parent is None:
            result = "[ ] -> "
        else:
            result = "{} -> ".format(self.parent.getName())
        result += self.getName()
        if self.depth is not None:
            result += "@{}".format(self.depth)
        result += " -> ["
        for child in self.children:
            result += " {}".format(child.getName())
        result += " ]"
        return result

    # add parent of self.
    # If already known, then we don't have to go futher up the chain and return False
    def addParent(self, parent):
        if parent.hexsha in Node.all:
            self.parent = Node.all[parent.hexsha]
            Node.all[parent.hexsha].children.append(self)
            return False
        self.parent = Node(parent, self)
        return True

    @staticmethod
    def addIfNeeded(commit):
        if commit.hexsha in Node.all:
            return Node.all[commit.hexsha]
        return Node(commit, None)

    def findDepth(self):
        if self.depth is not None:
            return self.depth
        if self.parent is None:
            self.depth = 0
            if Node.root is not None:
                raise ValueError('More than one root?')
            Node.root = self
        else:
            self.depth = self.parent.findDepth() + 1
        return self.depth

    @staticmethod
    def calcDepth():
        for node in Node.all.values():
            node.findDepth()

    def filesChangedIn(self):
        # print("finding files changed in {}".format(self.getName()))
        result = []
        for fname in self.commit.stats.files.keys():
            result.append(fname)
        return result

    def changesFromSplitOrBranchTo(self):
        start = self.parent
        files = {x: 1 for x in self.filesChangedIn()}
        while start and len(start.children) == 1 and start.name is None:
            for x in start.filesChangedIn():
                files[x] = 1
            start = start.parent
        return (start, files)


def namefield(name, maxlen=16):
    if len(name) > (maxlen-2):
        return name[:maxlen-(2+3)]+"...  "
    return name+" "*(maxlen-len(name))


def htmldiff(f, node):
    if node.name is not None:
        (src, changes) = node.changesFromSplitOrBranchTo()
        f.write('<div id="diff-{}" class="diffs"><h1>{} -> {}</h1>\n'.format(node.name, src.getName(), node.name))
        f.write('<ul><li>From: {}</li><li>To: {}</li></ul>\n'.format(datetime.fromtimestamp(src.commit.committed_date).strftime("%Y-%m-%d"),
                                                                     datetime.fromtimestamp(node.commit.committed_date).strftime("%Y-%m-%d")))
        changes = sorted(changes)
        for line in changes:
            f.write(' <li>{}</li>\n'.format(line))
        f.write('</ul></div>\n')
    for child in node.children:
        htmldiff(f, child)


def htmltree(depth, f, node):
    prefix = " "*depth
    f.write('{}<li><span id="{}" class="{}">{}</span>'.format(prefix, node.getName(), "sha" if node.name is None else "branch", node.getName()))
    if len(node.children) == 0:
        f.write('</li>\n'.format(prefix))
        return
    skipped = 0
    while len(node.children) == 1 and node.children[0].name is None:
        node = node.children[0]
        skipped += 1
    if skipped > 0:
        f.write(" +{}".format(skipped))
    f.write('\n{}<ul>\n'.format(prefix))
    for child in node.children:
        htmltree(depth+1, f, child)
    f.write('{}</ul></li>\n'.format(prefix))


def html(f, node):
    f.write('<head>\n')
    f.write('<link rel="stylesheet" href="tree.css">\n')
    f.write('<script src="tree.js"></script>\n')
    f.write('</head>\n')
    f.write('<body>\n')
    f.write('<div class="tree-diagram">\n')
    f.write('<ul>\n')
    f.write('<li class="tree-diagram__root">root\n<ul>')
    htmltree(0, f, node)
    f.write('</ul></li></ul></div>\n')
    f.write('<script>initialize();</script>\n')
    # now write out div's for each branch
    htmldiff(f, node)
    f.write('</body>\n')


################################################################
# main


allbranches = getAllBranches(remote=includeRemote)
pprint(allbranches)

# get all branches  (repo.heads is same)
if len(branches) == 0:
    branches = allbranches.keys()

# check that branches listed by user are valid
for branch in branches:
    if branch not in allbranches:
        print("{} not a known branch.".format(branch))

# build graph
for branchname in branches:
    branch = allbranches[branchname]
    leaf = Node.addIfNeeded(branch.commit)
    # print(leaf)
    leaf.name = branch.name
    # print(leaf)
    if leaf.parent:
        # this was already added, nothing to do
        continue
    while len(leaf.commit.parents) > 0:
        parent = leaf.commit.parents[0]
        more = leaf.addParent(parent)
        if not more:
            break
        leaf = leaf.parent

Node.calcDepth()
lca = Node.root
while len(lca.children) == 1:
    lca = lca.children[0]
print('First branch is at depth {}'.format(lca.depth))

# show all nodes after lca
if False:
    bydepth = sorted(Node.all.values(), key=lambda x: x.depth)
    for node in bydepth:
        if node.depth < lca.depth:
            continue
        print(node)

# show graph
row = [lca]
while True:
    nextrow = []
    connector = []
    numchildren = []
    idx = 0
    allnone = True
    # print this row
    for node in row:
        if node is None:
            sys.stdout.write("\t\t")
            nextrow.append(None)
            connector.append(idx)
            numchildren.append(0)
        else:
            sys.stdout.write(namefield(node.getName()))
            if len(node.children) == 0:
                nextrow.append(None)
                connector.append(idx)
                numchildren.append(0)
            else:
                numchildren.append(len(node.children))
                for child in node.children:
                    nextrow.append(child)
                    connector.append(idx)
                    idx += len(node.children)-1
                    allnone = allnone and child is None
    sys.stdout.write("\n")
    if allnone:
        break
    # trim off any None's at the end of nextrow
    revrow = nextrow[::-1]
    for nonelen in range(len(revrow)):
        if revrow[nonelen] is not None:
            break
    if nonelen > 0:
        nextrow = nextrow[:-nonelen]
    if idx > 1:
        # print("{} {} {}".format(idx, connector, numchildren))
        # we had a branch, so put an indicator in
        cc = "|"
        nodeIdx = 0
        inBranch = False
        # first row
        nextconnector = []
        for direc in connector:
            adjust = " " * 3
            filler = "\t\t"
            nextconnector.append("\\")
            if direc != 0:
                cc = "\\"
            numchildren[nodeIdx] -= 1
            if inBranch:
                adjust = "-" * 3
            if numchildren[nodeIdx] > 0:
                # more children from this node
                inBranch = True
                filler = "-" * 12
            else:
                inBranch = False
                filler = "\t\t"
                if numchildren[nodeIdx] < 0:
                    cc = " "
                    nextconnector[-1] = " "
                nodeIdx += 1
            sys.stdout.write("{}{}{}".format(adjust, cc, filler))
        sys.stdout.write("\n")
        # rest of rows
        for right in range(1, idx):
            for cc in nextconnector:
                adjust = " " * (right+3)
                filler = "\t\t"
                sys.stdout.write("{}{}{}".format(adjust, cc, filler))
            sys.stdout.write("\n")
    row = nextrow

with open('tree.html', "w") as outfile:
    html(outfile, lca)
exit(0)


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


# show untracked files on active branch
if False:
    untracked = repo.untracked_files
    pprint(untracked)

