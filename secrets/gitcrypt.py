#!/usr/bin/env python3

import argparser
import zuzserver
import json
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from timeit import default_timer as timer
import re
from pprint import pprint
import datetime

repobase = zuzserver.getRepobase()

parser = argparser.ArgumentParser(description="deal with files to be stored as encrypted in git")
parser.add_argument('-v', '--verbose', action="store_true", help="run in verbose mode")
parser.add_argument('-a', '--allfiles', action="store_true", help="do all files")
parser.add_argument('-d', '--decrypt', action="store_true", help="check for differences in decrypt")
parser.add_argument('-D', '--replace', action="store_true", help="do actual decrypt")
parser.add_argument('-e', '--encrypt', action="store_true", help="encrypt")
parser.add_argument('-s', '--specfile', default=".encrypt", help="file with encryption files relative to repo root")
parser.add_argument('-k', '--keyfile', default=".repokeys", help="file with keys relative to repo root")
parser.add_argument('files', nargs="*", help="specific files to operate on")
args = parser.parse_args()
verbose = args.verbose
doall = args.allfiles
replace = args.replace
decrypt = args.decrypt or replace
encrypt = args.encrypt
specfile = args.specfile
keyfile = args.keyfile

################################################################
# Helper functions

def error(msg):
    print(msg)
    exit(-1)

# recursively find all possible matches
def addTruePaths(start, matcher, files):
    names = os.listdir(start)
    for name in names:
        fullname = os.path.join(start, name)
        if os.path.islink(fullname):
            continue
        if os.path.isdir(fullname):
            addTruePaths(fullname, matcher, files)
        elif os.path.isfile(fullname):
            if matcher.search(fullname):
                files.append(fullname)
            

# parse spec file
def parseSpecfile(specfile):
    filelist = []
    filedict = []
    doSearch = False
    with open(specfile, "r") as spec:
        for line in spec:
            if line[0] == '#':
                # skip comments
                continue
            line = line.strip()
            if len(line) == 0:
                # skip blank lines
                continue
            if line[0] == "/":
                # this is relative to repo root
                filelist = os.path.join(repobase, line[1:])
            else:
                filedict.append("/"+re.escape(line)+"$")
                doSearch = True
    # now find all no anchored files (if any)
    if doSearch:
        regexp = re.compile("|".join(filedict))
        addTruePaths(repobase, regexp, filelist)
    return filelist


def encryptAndReplace(plain, secret, keyspec):
    if keyspec["derived"] is None:
        password = keyspec["password"]
        print("password", password)
        salt = b'saltsaltsaltsalt'
        print("salt", salt)
        start = timer()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        derived = kdf.derive(bytes(password, 'utf-8'))
        keyspec["derived"] = derived
        end = timer()
        print("kdf derived", derived, end-start)
        key = base64.urlsafe_b64encode(derived)
        print(key)
        f = Fernet(key)
        keyspec["fernet"] = f
    f = keyspec["fernet"]
    plainpath = plain
    secretpath = secret
    with open(plainpath, "rb") as plainfile:
        with open(secretpath, "wb") as secretfile:
            for line in plainfile:
                secretline = f.encrypt(line)
                secretfile.write(secretline)
                secretfile.write(b"\n")


def checkAndEncrypt(filepath, keylist, tocommit):
    stats = os.stat(filepath)
    pmtime = datetime.datetime.fromtimestamp(stats.st_mtime)
    (path, name) = os.path.split(filepath)
    neverFound = True
    for keyspec in keylist:
        user = keyspec["user"]
        efile = os.path.join(path, ".{}.{}".format(user, name))
        if os.path.isfile(efile):
            neverFound = False
            stats = os.stat(efile)
            emtime = datetime.datetime.fromtimestamp(stats.st_mtime)
            if emtime < pmtime:
                # encrypted file is older than plain file, so it needs to be re-encrypted and committed
                encryptAndReplace(filepath, efile, keyspec)
                print("Updated {}".format(efile))
                tocommit.append(efile)
                break
    if neverFound:
        # no encrypted version found, so create encrypted version using repo key
        repokey = keylist[-1]
        user = repokey["user"]
        efile = os.path.join(path, ".{}.{}".format(user, name))
        print("Creating {}".format(efile))
        encryptAndReplace(filepath, efile, repokey)
        tocommit.append(efile)


# check if 'filepath' a plaintext file needs to be updated because
# it's associated secret file is different and newer
def checkAndDecrypt(filepath, keylist, changed, replace):
    stats = os.stat(filepath)
    pmtime = datetime.datetime.fromtimestamp(stats.st_mtime)
    (path, name) = os.path.split(filepath)
    neverFound = True
    for keyspec in keylist:
        user = keyspec["user"]
        efile = os.path.join(path, ".{}.{}".format(user, name))
        if os.path.isfile(efile):
            neverFound = False
            stats = os.stat(efile)
            emtime = datetime.datetime.fromtimestamp(stats.st_mtime)
            if emtime > pmtime:
                # encrypted file is newer than plain file, so it needs to be decrypted
                encryptAndReplace(filepath, efile, keyspec)
                print("Updated {}".format(efile))
                tocommit.append(efile)
                break
    if neverFound:
        # no encrypted version found, so create encrypted version using repo key
        repokey = keylist[-1]
        user = repokey["user"]
        efile = os.path.join(path, ".{}.{}".format(user, name))
        print("Creating {}".format(efile))
        encryptAndReplace(filepath, efile, repokey)
        tocommit.append(efile)
    


################################################################
# check parameters make sense

if decrypt and encrypt:
    error("Can't do both encrypt and decrypt at same time")

################################################################
# process files and keys

# get plaintext files to process
targets = args.files
files = None
if len(targets) > 0:
    # we ignore specfile and use files specified on command line
    files = args.files
else:
    # check and make sure specfile exists
    maybefile = specfile
    if not os.path.isfile(maybefile):
        maybefile = os.path.join(repobase, specfile)
        if not os.path.isfile(maybefile):
            error("{}: Could not find specfile or in {}".format(specfile, maybefile))
    files = parseSpecfile(maybefile)
pprint(files)

# get keys
maybefile = keyfile
if not os.path.isfile(maybefile):
    maybefile = os.path.join(repobase, keyfile)
    if not os.path.isfile(maybefile):
        error("{}: Could not find keyfile or in {}".format(keyfile, maybefile))
with open(maybefile, "r") as infile:
    keystring = infile.read()
keys = json.loads(keystring)
keylist = []
for key in keys.keys():
    keylist.append({"user": key, "password": keys[key], "derived": None})
pprint(keylist)
keylist = sorted(keylist, key=lambda x: x["user"], reverse=True)
pprint(keylist)

if encrypt:
    # look for files that need to be committed
    tocommit = []
    for file in files:
        checkAndEncrypt(file, keylist, tocommit)
    if len(tocommit) > 0:
        # some of the files changed, so exit -1
        print("There are {} secret files that changed".format(len(tocommit)))
        exit(-1)
    exit(0)

if decrypt:
    # see if any secret files are newer than plain files.  Before we
    # decrypt make sure plain files haven't been changed
    changed = []
    for file in files:
        checkAndDecrypt(file, keylist, changed, replace)
    if len(changed) > 0:
        print("There are {} plaintext files that {}changed".format(len(changed), "need to be " if replace else ""))
    exit(0)




password = b"password"
print("password", password)
salt = b'saltsaltsaltsalt'
print("salt", salt)
start = timer()
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=480000,
)
derived = kdf.derive(password)
end = timer()
print("kdf derived", derived, end-start)
key = base64.urlsafe_b64encode(derived)
print(key)
f = Fernet(key)
print("f", f)
plainpath = "/home/seth/scripts/gitcrypt.py"
secretpath = "/tmp/encrypted.gitcrypt.py"
newplainpath = "/tmp/decrypted.gitcrypt.py"
start = timer()
with open(plainpath, "rb") as plainfile:
    with open(secretpath, "wb") as secretfile:
        for line in plainfile:
            secretline = f.encrypt(line)
            secretfile.write(secretline)
            secretfile.write(b"\n")
end = timer()
print("Encryption: ", end-start)
start = timer()
with open(secretpath, "rb") as secretfile:
    with open(newplainpath, "wb") as plainfile:
        for line in secretfile:
            plainline = f.decrypt(line)
            plainfile.write(plainline)
end = timer()
print("Decrypt: ", end-start)
