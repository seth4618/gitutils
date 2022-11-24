# Tools for using git

## Installation

I use a virtual environment and the path for these scripts points
there, so you should edit the first line of python files to point to
your python.  You will also need to install at least GitPython, i.e.,
`pip install gitpython`.  Or, after you clone, use the
[requirements.txt](./requirements.txt) file in this directory with
`pip install -r requirements.txt`

## utils

- `findcommon.py`: Find out what is common/different between two
  branches.
- `bgraph.py`: Show the graph of the commit's from the first common
  ancestor to specified branch names.  Generate a text output and an
  html file, `tree.html` which is little nicer.  You can click on
  various nodes and see which files changed from last branch point to
  the specified node.

## other files

- tree.css and tree.js are used to render the output of bgraph.py.
  
