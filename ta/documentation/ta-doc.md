# UTA Relevant Documentation

## How to grade

1. Login to a department machine.
2. Open a terminal (ctrl-alt-t usually)
3. Run `cs111-grade`. If you get a command not found error:
    - talk to someone who knows bash about adding `/course/cs0111/tabin` to
    your PATH, or
    - run `/course/cs0111/tabin/cs111-grade`.
4. Open your browser and go to `0.0.0.0:6924`
5. Start grading! There are buttons that will help at the bottom of the page,
and at the top of the page there is a button to view the student code.

### Grading remotely
If you want to grade remotely, you should
1. ssh in to a department machine
2. run `hostname` to figure out which computer you are on
3. run `cs111-grade`
4. On your machine, open a terminal and run this command:
    `ssh CSLOGIN@ssh.cs.brown.edu -N -L 6924:HOSTNAME:6924`
(replacing the login with your login and the hostname with the hostname
of the computer running the grading app)

### Updated grading app
The grading app has been updated after the Fall 2018 semester ended.

The major changes are:

#### New comments
- You can now drag comments around to re-order them. *This means that the order
you give comments in is the order they will show up in on the student's grade
report* (before it was based on comment length).
- You can now click away from comments without losing your progress.
- You can now left click comments to edit them.
- You can now delete old comments.
- To make a comment usuable by all TAs, **right click** on the comment.

#### Fudge points
Every category will have an option for you to give a student fudge points.
If you are using numerical grading (not category grading like Check Check Plus
etc) you should explain why you are giving the fudge points and how many
in a comment.

#### Rubrics
Point values are now displayed for each rubric category (i.e. out of 14 points)
and for each rubric option.

#### Emoji
If a student did a great job, you can select the checkbox at the bottom of
the grading form to give them a text art emoji like this:
```
   /                       \
 /X/                       \X\
|XX\         _____         /XX|
|XXX\     _/       \_     /XXX|___________
 \XXXXXXX             XXXXXXX/            \\\
   \XXXX    /     \    XXXXX/                \\\
        |   0     0   |                         \
         |           |                           \
          \         /                            |______//
           \       /                             |
            | O_O | \                            |
             \ _ /   \________________           |
                        | |  | |      \         /
  Good work!          / |  / |       \______/
                      \ |  \ |        \ |  \ |
                      __| |__| |      __| |__| |
                      |___||___|      |___||___|
```

Note that the emoji given is randomly selected and will not be the same one
on the student's emailed report as the one you will see if you click
the `View report` button.

## How to write rubrics

### JSON

To be able to write rubrics, you should have an idea of what JSON is. At a
high level, JSON is a format for data and is an easy way to store data in a
file. To learn more about JSON, read this link:
https://realpython.com/python-json/
You definitely don't need to read the whole article; just get the idea of
what JSON is and if you want, how to interface with it using Python. No need
to read the "A Real World Example (sort of)" example.

### Rubrics
Each Assignment is comprised of a list of Questions. Each Question has a single
file associated with it that students will upload. For example, Homework 2
might have a `safety.arr` and `reflections.txt` questions. That means two
rubrics need to be written for homework 2.

The directory structure may then look like this:
```
/ta/grading/data/rubrics
    ...
    homework2
        q1.json # rubric for safety.arr
        q2.json # rubric for reflections.txt
```

Each rubric is a dictionary. At the top level, the dictionary has three keys:

- `emoji`: value is a boolean, whether or not the student gets an ascii art
emoji for their handin. For rubrics you put in `/ta/grading/data/rubrics`
(question-level rubrics), this value should be `false`.
- `comments`: a dictionary of given and `un_given` comments. For
question-level rubrics, the given key should have an empty list value, and
the `un_given` key should have a list of any global comments as the value.
- `rubric`: a dictionary with one key per grade category (with the key
describing the grade category) and the value being a dictionary with
a comments key, a `rubric_items` key, and a `fudge_points` key.
- The fudge points key should have a list with two floats in it as its
value. For question-level rubrics, the first value should be 0.0 as it is
the number of fudge points given. The second value should be the (positive)
maximum number of fudge points to allow giving.

Once you have written a rubric, check that is valid by running
`cs111-check-rubric path-to-rubric.json`

For example:
`cs111-check-rubric /course/cs0111/ta/grading/data/rubrics/homework2/q1.json`

### Rubric Example

```json
{
    "emoji": false,
    "comments": {
        "given": [],
        "un_given": ["Great work!"]
    },
    "rubric": {
        "Functionality": {
            "fudge_points": [0.0, 10.0],
            "comments": {
                "given": [],
                "un_given": ["Your base case for append is wrong; ..."]
            },
            "rubric_items": [
                {
                    "descr": "Base case for append",
                    "selected": null,
                    "options": [
                        {
                            "descr": "Correctly returns second list",
                            "point_val": 3
                        },
                        {
                            "descr": "Incorrectly returns first list",
                            "point_val": 1
                        },
                        {
                            "descr": "No attempt",
                            "point_val": 0
                        }
                    ]
                },
                {
                    "same keys": "same value types"
                }
            ]
        },
        "More categories": {
            "same": "same value types"
        }
    }
}
```

## How to write testsuites

You can see an example of a Python testsuite in
`/ta/grading/data/tests/fun.py`. If you want to modify the testsuite
infrastructure, you will need to go into the `testing_helpers.py` file.

The grading app already knows how to run Python testsuites. If you want to try
Pyret testsuites, go for it, but it's super slow and you don't get good info
out of it so I recommend having Pyret testsuites just print out what to copy
paste into Pyret and then just run it in browser.

For Python, there is a more involved infrastructure for writing testsuites.
If you want the testsuite results to feed into the student's grade
automatically, you will need to update the code for that (see the 
[customization documentation](customization.html#customizing-testsuites)).

`fun.py` is a testing file where students might write a two functions,
`append` and `remove-3s`.

If you want to add new languages, look at the
[customization documentation](customization.html#customizing-testsuites). It
shouldn't be too difficult!
