# Installation

## Test installation

1. Download and rename to /course/cs0111 (yes in root directory, sorry).
2. Install the virtual environment with Python 3.7 (`virtualenv venv -p $(which python3.7)`)
3. Make a groups folder `/ta/groups`
    - Run `touch tas.txt htas.txt students.txt students.csv`
    - Put your username into tas.txt, htas.txt, and students.txt. Put username,name,email into students.csv

## Real installation

1. Download the repo and move it to /course/name-of-your-course so the directory structure looks like
    ```
    | course
      | your-course (i.e. cs0111)
        | ta
        | hta
    ```
2. You will need to maintain a list of students in the course, of tas logins, and of htas logins.

    Set this up by modifying /htabin/update-groups (try running it and checking the contents of `/hta/groups/` to see if it works for your course). you may need to run kinit before running update-groups.

    For the handin and grading apps to work properly, there need to be 4 files in `/hta/groups`:
    1) `students.txt` - a newline separated list of student CS logins in the course
    2) `students.json` - a JSON file with a list of lists each with 3 elements: [login, email, name] of each student in the class
    3) `tas.txt` - a newline separated list of the CS logins of the TAs for the course
    4) `htas.txt` - a newline separated list of the CS logins of the HTAs for the course

3. 

### Handin setup
The handin system uses Google Forms (by default).


3. The grading app by default will collect grades as a hashtable of category -> number of points in that category. For example, if an assignment has a rubric with Functionality and Code Style categories, a student's raw grade may look like:
```python
{
    "Functionality": 12,
    "Code Style": 5.3
}
```

How this is converted to the student's final grade is up to the course. The function for converting from a raw grade to the final grade is in `/ta/course_customization.py` in the `determine_grade` function.

4.


