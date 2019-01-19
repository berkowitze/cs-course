# HTA Relevant Documentation

## `assignments.json`
For general configuration, use `ta/assignments.json`. This file contains pretty much all
the configuration for the course.
- What Google Sheet to look for handins in
- Who to send error emails to
- Data for each assignment
    - Which questions go on each assignment
    - When assignments are due
    - Group/project data for each assignment, if relevant
    - Whether grading is anonymous
    - Grading status
    - Information for testsuites for each question

For grading, almost everything HTA specific can be done with two commands which are in `htabin`:

## `cs111-asgn-hub`
This script his gives a command line interface with the course and
individual assignments. Use this to:
- Start, finish, and reset grading
- View flagged handins
- Generate and send grade reports
- Manage regrading and de-anonymization
- Generate gradebook
- Generate and send grade summaries
- Manage course data backups
- Reset course data for the next semester

## `asgnipython`
This gives a python interface with the correct permissions
and everything from `hta_classes.py` loaded. the most useful time to use
`asgnipython` is for updating rubrics during grading; see the 
[hta\_classes.py documentation](hta_classes.html) for the classes, variables,
and methods available. the `magic_update` function is how you update rubrics.
you may also want to use `asgnipython` to force the reset of assignment grading
by doing `HTA_Assignment("Assignment Name").reset_grading(True)`.
