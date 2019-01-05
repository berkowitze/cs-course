function dir-make {
    if [ ! -d "$1" ]; then
        mkdir "$1"
    else
        echo "$1 already exists, skipping..."
    fi;
}

read -p "Enter a Python 3.7 path (i.e. /local/bin/python3.7): " PYTHONPATH;

if [ -x $PYTHONPATH ]; then
    res=`$PYTHONPATH -c "import sys; print('%s.%s' % (sys.version_info.major, sys.version_info.minor))"`
    if [[ $res != "3.7" ]]; then
        echo "invalid python executable (got version $res, needed 3.7)"
        exit 1;
    fi;
else
    echo "got non-executable path for python installation"
    exit 1;
fi;
virtualenv -p $PYTHONPATH "./ta/venv";
./ta/venv/bin/pip install -r ./ta/requirements.txt;
exit 0;

if [ ! -e ./tabin ];
then
    echo "in invalid directory, run from cs-course root"
    exit 1
fi;

dir-make "./ta/groups"

if [ -f ./ta/groups/tas.txt ];
then
    echo "./ta/groups files already exist, not overwriting..."
else
    echo "$USER" > ./ta/groups/tas.txt;
    echo "$USER" > ./ta/groups/htas.txt;
    echo "$USER" > ./ta/groups/students.txt;
    echo "$USER,$USER@cs.brown.edu,Full Name"> ./ta/groups/students.csv;
fi;

dir-make "./ta/grading/data/grades"
dir-make "./ta/grading/data/sfiles"
dir-make "./ta/grading/data/logs"
dir-make "./ta/grading/data/projects"
dir-make "./ta/grading/data/anonymization"
dir-make "./ta/grading/data/blocklists"
dir-make "./ta/grading/data/tests"

dir-make "./ta/grading/data/logs/testingassignment"
if [ ! -e ./ta/grading/data/logs/testingassignment/q1.json ]; then
    cp tests/* ./ta/grading/data/logs/testingassignment
else
    echo "testingassignment log file already exists, skipping..."
fi;

virtualenv -p `which python3.7` "./ta/grading/venv"
soruce ./ta/grading/venv/bin/activate
pip install -r "./ta/grading/requirements.txt"
