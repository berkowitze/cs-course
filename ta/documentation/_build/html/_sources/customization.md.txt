# Customizing the grading/handin scripts

All scripts for the system are written in Python and are (largely) documented,
so *hopefully* it won't be that hard to customize things to match your needs.

Before changing anything, it's a good idea to understand the
[filesystem](filesystem.html) of the repository, and have a good understanding
of the
[Python typing module](https://docs.python.org/3/library/typing.html). All
scripts are written in Python 3.7 and use the `/ta/venv` virtual environment.

## Customizing the grading app website
**Difficulty**: Depends on what you're doing... probably not that bad.

All code specific to the web app can be found in the `/ta/grading` folder.
The most relevant files there are `static/main.js`, `templates`, and
`grading_app.py`. The web app interfaces with `classes.py` which handles the
logic of extracting, saving, running tests, etc.

## Customizing testsuites
**Difficulty**: Easy from the grading app perspective, but you'll have to
write the testsuite scripts.

If you want to add a new language (right now there is just Python and Pyret),
go to `/ta/grading/classes.py` and look for the `run_test` `Handin` method.

From there, it should be relatively self-explanatory; the `python_test`
method should give you an idea of how to start.

The other thing you need to do is make sure that when you add questions to
`/ta/assignments.json`, the `"ts_lang"` attribute of each question is set to
the correct file extension; it is in `run_test` that you use this extension.
So if you are adding Java support, you might put `"ts_lang": "Java"` in
`assignments.json` for any questions using java testing, then add an if
statement in `run_test` that calls the appropriate method
`if test_type == 'Java'`.

## Customizing handin
**Difficulty**: Easy to moderate depending on what you're doing

If you do not want to use Google Forms for handin, or would like to use Google
Forms in a different way, that is probably fine as long as you stick with
the current framework of "each question has one file" and put things into the
`/hta/handin/students/login/asgn-name/#-submission/files` directories.

This directory works as follows:

Each student gets their own directory. Each student directory has one directory
per assignment. In each assignment directory, there will be one directory per
submission. The submission directory names should follow
(sub-numb)-submission(-late). When grading starts, the latest submission will
be copied to the grading directory for the grading app to work properly.

Note: you should either require students to submit the proper filenames and
reject any files that do not exactly match, or rename files to the proper
filename and warn students you have done so (the default in this system).

The grading app will not be able to handle filenames differing from what is
expected (it won't break anything but it just won't work for testsuites etc.).

The late flag should be used for late submissions, and will be passed as a
boolean parameter to the function that determines a student's grade.

For example:
```
/hta/handin/students
    eberkowi
        homework1
            1-submission
                flags.arr
            2-submission
                flags.arr
            3-submission-late
                flags.arr
```

If you need to modify this directory structure, the scripts that will need to
be modified are:
- `/hta/handin/check_submissions.py`
- `/hta/grading/hta_classes.py` under the `_generate_report` method

## Changing grading rubric format
**Difficulty**: V annoying

Avoid doing this if you can. If you don't want categorized grading, just
change how reports and grades are generated
(see [below](#customizing-grade-reports)).

The type for a rubric is laid out in `/ta/grading/custom_types.py`
and is used for rubric validation and assumed as the format for all rubrics
for all assignments. If you change the type of this, you should run `lintall`
to check where you will need to update code logic to match your new types.

You will also need to change how the web app renders the rubric. The logic
for this is almost entirely in `/ta/grading/static/main.js` and
`/ta/grading/templates/rubric.html`. You will also need to handle how the
Flask application handles when a TA saves a rubric, which will be in
`/ta/grading/grading_app.py` under the `save_handin` route and in
`/ta/grading/classes.py` under the `save_data` method.

Finally, you will need to change how rubrics are converted to raw grades
in `/ta/grading/course_customization.py` under the `generate_grade_report`
method.

This will also break some of the scripts in `/tabin` and `/htabin` though
I don't think anything critical. `lintall` should help.

I would highly recommend against changing rubric format during the semester.

## Customizing grades and grade reports
**Difficulty**: Hopefully not that bad

Customizing grades shouldn't be that bad. The types for RawGrade and Grade
are outlined in `custom_types.py`. The flow is `Rubric -> RawGrade -> Grade`.
I would mess only with the `RawGrade -> Grade` bit, which is in the
`determine_grade` function in `/ta/grading/course_customization.py` file.

If possible, stick with grades being strings floats or dictionaries of strings
mapping to either floats or strings, so nothing will have to be updated except
how reports and grades are generated in `course_customization.py`.

**Example**: You want all grades to be numeric. You would go to
`course_customization.py` and change `determine_grade` to output something like
"52 / 60" (summing the student's points / summing the total possible points).

**Example**: You want to use a different grading scheme for one assignment.
You would go to  `course_customization.py` and under `determine_grade` add
logic to check which assignment is being graded or how to read the bracket file
so that it outputs `"52 / 60"` for certain assignments and
```python
{
    "Functionality": "13 / 15",
    "Clarity": "12 / 16"
}
```
for others.

## Customizing grade reports
**Difficulty**: Relatively easy?

The logic for grade report generating is in the `get_handin_report_str` 
function in `/ta/grading/course_customization.py` and the `_generate_report`
method in `/hta/grading/hta_classes.py`.
