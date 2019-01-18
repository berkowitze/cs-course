# Getting started

This repository allows courses to manage handin and grading for a computer
science course with a wide level of customizability. By default, the system
includes anonymous grading, TA/student blocklisting,
group and multi-part assignments, assignments with multiple questions
or zip file handins, automatically sending grade reports, testsuites, and more.
There are also scripts for handling lab checkoff and allocation.

As the app is relatively new, there are certainly bugs or missing features.
Hopefully things are documented and laid out in such a way that implementing
features or customizing the app for your own course isn't that difficult, but
if it is email me (eliberkowitz@gmail.com) and I'll be happy to help :)

## Documentation to read
- [Scripts and grading for TAs](ta-doc.html) (recommended for all HTAs and UTAs)
- [Scripts, grading, handin, and more for HTAs](hta-doc.html)
(recommended for HTAs  maintaining infrastructure, regrading,
and mid-grading rubric updates).
- [Customizing the system for different courses](customization.html)
- [App Filesystem](filesystem.html)
- First time setup
- Yearly setup

## What the flow looks like for students

1. Student hands in work on a Google Form (which are generally very intuitive
to figure out how to upload files to).

2. A minute or two later, they receive a confirmation email of their handin.

3. After the TAs grade the assignment, the student will receive an email with
their grade report and the emails of any TA they should contact in case of a
grade complaint.

## What the flow looks like for TAs

### Grading
1. To grade, TAs run `cs111-grade` on a department machine, which boots up a
local Flask application to manage grading handins. They log into the
application using a password set once at the beginning of the semester, and
start grading.

2. For each handin, they will fill out a series of dropdowns and give comments
to the students. It is up to the course how to turn these values and comments
into grades and grade reports. The TA can flag the handin for HTA review,
view the student's code, run testsuites, save the handin temporarily and move
on to the next while they wait for help, etc. all in browser (no need to
have a dozen windows open).

3. Click "Save & Done" and move on to the next handin!

#### Regrading
1. Go to `/ta/grading/grades/tas-login/assignment/student` and modify the
relevant grades.

2. Depending on the grading scheme, the TA can notify the HTAs that a grade
has changed and the HTAs can fully regenerate the students report, or the
TA can directly make an override using the `/tabin/make-override` script
then modifying the `grade-override.json` and `report-override.txt` files.

3. The TA notifies an HTA that something has changed and the HTA will
make sure the grade has been updated properly and email the student
their updated report.

### Rubrics
If a TA is working on a rubric, they will go to
`/ta/grading/data/rubrics/asgn-name/q#.json` and enter a JSON file with the
rubric for the assignment in it. This is probably the most tedious part of the
grading app as writing raw JSON is frustrating, but once you've done it once
or twice it's not that bad. There are scripts to check that a rubric has been
written correctly in `/tabin/cs111-check-rubric`.

## What the flow looks like for HTAs

As the flow is meant to be easy for students and TAs, a lot of the work falls
onto the HTAs. I did my best to simplify things as much as possible though!

### One-time setup
There is a good amount of setup needed before the semester starts. The handin
system needs the credentials of a Google account with a API client set up,
and the system needs files with information about the students taking the class
to function properly. This setup process is documented in ADD LINK.

After this one-time setup is done, the next year all the HTAs should need to do
is run `cs111-asgn-hub` and reset the course (which backs up then clears all
student-related files and resets all grading/handin progress)

### Weekly setup
1. Every time there is a new assignment, it needs to go into
`/ta/assignments.json`. There is a script to add new assignments in the proper
format to this JSON file in `/ta/cs111-add-asgn`. The JSON is used for both 
handin and grading so the same information doesn't need to be entered twice.

2. When grading needs to start for an assignment, the HTA runs `cs111-asgn-hub`
and starts the grading.

3. Once grading is complete, the HTA runs `cs111-asgn-hub` to generate grade
reports. Once the grade reports are reviewed (either by eye or using some
script), grade reports are sent through `cs111-asgn-hub`.

4. The HTA can optionally run `cs111-asgn-hub` to deanonymize assignments so
that TAs can do grade adjustments.

### Regrading
HTAs can do grade overrides in the same way TAs do, and can email them to
students using `cs111-asgn-hub`. They can also use `cs111-asgn-hub` to
regenerate reports for individual students.
