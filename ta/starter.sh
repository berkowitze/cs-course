# navigation


# variables
dirname="cooldir"              # make a locally available variable
export newdirname="coolername" # make a globally available variable
python -c "import os; print os.getenv('dirname')"    # will output None
python -c "import os; print os.getenv('newdirname')" # will output "coolername"


# printing
echo hello
echo dirname
echo $dirname

# making folders and files
#mkdir
#mkdir -p 

# modifying files (copying, renaming, deleting)

# symbolic links

# permissions

# PATH
echo $PATH
export PATH="$PATH:$HOME/bin"

# virtual environments

# htas: look at setfacl for files that owner/group/world is not adequate
# to handle (setfacl -m g:cs-0111ta:rx filename gives cs-0111tas rx access
# only to that file, regardless of owner/group)
