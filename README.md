# Installation

## Test installation

1. Download and rename to /course/cs0111 (yes in root directory, sorry).
2. Install the virtual environment with Python 3.7 (`virtualenv venv -p $(which python3.7)`)
3. Make a groups folder `/ta/groups`
    - Run `touch tas.txt htas.txt students.txt students.csv`
    - Put your username into tas.txt, htas.txt, and students.txt. Put username,name,email into students.csv

## Real installation

1. Download the repo and move it to /course/<name-of-your-course>
2. You will need to maintain a list of students in the course, of tas logins, and of htas logins.

    Set this up by modifying /tabin/update-groups (try running it and checking the contents of /hta/groups/ to see if it works for your course). you may need to run kinit before running update-groups

### Handin setup
The handin system uses Google Docs


