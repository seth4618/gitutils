# Tools to handle storing secrets in a repo

Many projects require some secrets which should not be committed to a
repo.  This creates a maintenance and on-boarding nightmare.  Further
complicating the situation is that the secrets are often different for
different environments.  Secrets used on production are different than
those on testing machines and they could also be different for each
developer.  Encrypting the secret files in their entirety and storing
them in the repo is less than ideal because then changes can't be
tracked.

Our solution is a combination of config files, git hooks, and some
command wrappers which store each secret file in the repo encrypted on
a line-by-line basis.  Each secret file will potentially be stored in
the repo multiple times, once for each environment they are used in.

## Config files

These config files are stored in the root of the repo.

- `.repokeys`: This file is NOT stored in the repo and contains the
  passwords used to encrypt/decrypt the secret files.  It has keys for
  hostnames and users to allow the proper secrets to be used in each
  use case.
- `.encrypt`: This file contains the files which hold secrets.

## How files are stored

Each file in the `.encrypt` file will be stored in the repo once for
each environment for which it is defined, as follows:

_filename_ will be stored as `.`_id_`.`_filename_ in the repo, where
_id_ is a key in the `.repokeys` file.  It can be a hostname, and
environment variable, a userid, or `-`.  The use of the `-` is the
default which applies if no other _id_'s apply.

## Management

On commit, a pre-commit hook checks to see if any of the plaintext
files have been updated by comparing encrypting them and comparing
them to the encrypted files on disk.  If they are different it reports
an error causing the commit to abort.  This allows the user to encrypt
the files.

On checkout, **not sure what to do here that is easy for the user**


## example

### .repokeys


