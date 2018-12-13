function dir-make {
    if [ ! -d "$1" ]; then
        mkdir "$1"
    else
        echo "$1 already exists, skipping..."
    fi;
}

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
