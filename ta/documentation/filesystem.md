# Filesystem

The grading app assumes a certain filesystem. Changing the directory structure
is possible, but will require updating scripts to make sure nothing breaks.

TAs do not need pretty much any understanding of the filesystem, but being
familiar with the `/ta/grading/grades` and `/ta/grading/data/rubrics`
folders will be helpful.

HTAs should have an understanding of what files are where for handin, grading,
and final grades. In particular, they should know what is in the
`/ta/grading/data`, `/ta/grading/grades`, `/hta/handin/students`, `/hta/grades`,
`/hta/summaries`, `/tabin` and `/htabin` directories.

Below is a relatively full view of the filesystem with scripts largely taken
out to make it somewhat readable:

```
.
├── hta
│   ├── grades
│   │   ├── student-login
│   │   │   ├── assignment-name
│   │   │   │   ├── code
│   │   │   │   ├── grade.json
│   │   │   │   ├── report.txt
│   │   │   │   └── rubric-summary.txt
│   │   └── ...
│   ├── grading
│   │   ├── add-student-submission
│   │   ├── anonymization
│   │   │   ├── assignment-name.json
│   │   │   └── ...
│   │   └── lab-exceptions.txt
│   ├── groups -> ../ta/groups
│   ├── handin
│   │   ├── students
│   │   │   ├── student-login
│   │   │   │   ├── homework1
│   │   │   │   │   ├── 1-submission
│   │   │   │   │   │   └── submitted-files
│   │   │   │   │   └── 2-submission-late
│   │   │   │   ├── homework2
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── submission_log.txt
│   ├── s-t-blocklist.json
│   └── summaries
│       ├── student-login.txt
│       └── ...
├── htabin
│   ├── asgnipython
│   ├── better-members
│   ├── cs111-asgn-hub
│   ├── cs111-check-handins
│   ├── cs111-get-grade-data
│   ├── group-data
│   ├── hta-ta-file
│   ├── lintall
│   ├── login-to-email
│   ├── mossScript
│   └── update-groups
├── lintfiles
├── setup.sh
├── ta
│   ├── assignments.json
│   ├── documentation
│   ├── grading
│   │   ├── bracket.json
│   │   ├── classes.py
│   │   ├── course_customization.py
│   │   ├── custom_types.py
│   │   ├── data
│   │   │   ├── anonymization
│   │   │   │   ├── homework-name.json
│   │   │   │   └── ...
│   │   │   ├── blocklists
│   │   │   │   ├── homework-name.json
│   │   │   │   └── ...
│   │   │   ├── grades
│   │   │   │   ├── homework-name
│   │   │   │   │   ├── student-0.json
│   │   │   │   │   └── ...
│   │   │   ├── labs
│   │   │   │   ├── allocate.py
│   │   │   │   ├── exceptions.txt
│   │   │   │   ├── l1-email.html
│   │   │   │   ├── l2-email.html
│   │   │   │   ├── l3-email.html
│   │   │   │   ├── l4-email.html
│   │   │   │   ├── attendance.json
│   │   │   │   ├── lab-data.json
│   │   │   │   └── roster.json
│   │   │   ├── logs
│   │   │   │   ├── assignment-with-2-questions
│   │   │   │   │   ├── q1.json
│   │   │   │   │   └── q2.json
│   │   │   │   └── ...
│   │   │   ├── projects
│   │   │   │   ├── project1.json
│   │   │   │   └── ...
│   │   │   ├── rubrics
│   │   │   │   ├── assignment-with-2-questions
│   │   │   │   │   ├── q1.json
│   │   │   │   │   └── q2.json
│   │   │   │   └── ...
│   │   │   ├── sfiles
│   │   │   │   ├── homework-name
│   │   │   │   │   ├── student-0
│   │   │   │   │   │   ├── student-code-file-1
│   │   │   │   │   │   └── student-code-file-2
│   │   │   │   │   └── ...
│   │   │   │   └── ...
│   │   │   └── tests
│   │   │       ├── homework1
│   │   │       │   ├── filename.py
│   │   │       └── ...
│   │   ├── grades
│   │   │   ├── ta-login
│   │   │   │   ├── asgn-name
│   │   │   │   │   └── student-grades
│   │   │   └── ...
│   │   ├── grading_app.py
│   │   ├── passwd_hash.txt
│   │   ├── static
│   │   │   ├── files-for-grading-app-site
│   │   │   └── ...
│   │   ├── templates
│   │   │   ├── files-for-grading-app-site
│   │   │   └── ...
│   │   └── todo
│   ├── groups
│   │   ├── htas.txt
│   │   ├── students.csv
│   │   ├── students.txt
│   │   └── tas.txt
│   ├── requirements.txt
│   └── t-s-blocklist.json
└── tabin
    ├── clean-json
    ├── clear-comments
    ├── cs111-add-asgn
    ├── cs111-blocklist
    ├── cs111-check-rubric
    ├── cs111-grade
    ├── cs111-lab-checkoff
    ├── cs111-lab-switch
    ├── cs111-rubric-info
    ├── cs111-update-web
    ├── custom_types.py -> ../ta/grading/custom_types.py
    ├── email-to-login
    ├── helpers.py -> ../ta/grading/helpers.py
    ├── make-override
    ├── print_results.py
    ├── prompts.py
    ├── pyret-test
    ├── python-test
    └── update-documentation

```