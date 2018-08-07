import os
base = '/course/cs0111'

def determine_grade(possibilities, ranges, score):
    ''' given a list of grade possibilities (strings), a list of grade
    ranges (with length two less than `possibilities`), and a
    numeric score, determines the grade that the score has deserved.
    - uses [inclusive, exclusive) ranges;
    - if score is None, gives the first element of possibilities
    - below the bottom number of ranges is the second element of possibilities
    - above the top number of ranges is the last element of possibilities
    - anything else is determined by checking which range the score is between
    using [inclusive, exclusive) ranges. '''
    if score is None: # no grade
        return possibilities[0]

    assert isinstance(score, (int, float)), \
            'nonscore %s in determine_grade' % score
    
    if score < ranges[0]:
        return possibilities[1]
    elif score >= ranges[-1]:
        return possibilities[-1]
    else:
        # not gonna be second lowest grade or highest grade, with C/CP/CM
        # there's only one other option but figure it out anyway
        for i, lower in enumerate(ranges[:-1]):
            upper = ranges[i + 1]
            if score >= lower and score < upper:
                return possibilities[i + 2]

        raise Exception('Error that shouldn\'t happen damn')

# TODO this really needs to get cleaned up
def get_student_list():
    spath = os.path.join(base, 'ta', 'students.txt')
    with open(spath) as f:
        logins = map(str.strip, f.read().strip().split('\n'))

    grade_paths = map(lambda f: os.path.join(base, f), logins)
    return logins, grade_paths

def load_students(path=os.path.join(base, 'hta', 'grading', 'students.txt')):
    ''' todo this needs to be cleaned up as well '''
    students = []
    with open(path, 'r') as f:
        lines = f.read().strip().split('\n')
        for line in lines:
            row      = line.split(' ')
            email    = row[0]
            username = row[1]
            students.append((email, username))

    return students

def email_to_login(email):
    students = load_students()
    for student in students:
        if student[0] == email:
            return student[1]

    raise Exception('Student %s not found.' % email)

def login_to_email(login):
    students = load_students()
    for student in students:
        if student[1] == login:
            return student[0]

    raise Exception('Student %s not found.' % login)

if __name__ == '__main__':
    # run some tests if on __main__ (not being imported)
    testing_ps = ['No grade', 'CM', 'C', 'CPM', 'CP']
    testing_rngs = [2, 4, 5]
    assert determine_grade(testing_ps, testing_rngs, None) == 'No grade'
    assert determine_grade(testing_ps, testing_rngs, 0) == 'CM'
    assert determine_grade(testing_ps, testing_rngs, 3) == 'C'
    assert determine_grade(testing_ps, testing_rngs, 4) == 'CPM'
    assert determine_grade(testing_ps, testing_rngs, 5) == 'CP'
    assert determine_grade(testing_ps, testing_rngs, 2) == 'C'
    assert determine_grade(testing_ps, testing_rngs, 2.0) == 'C'
    assert determine_grade(testing_ps, testing_rngs, 4.5) == 'CPM'
    assert determine_grade(testing_ps, testing_rngs, 4.0) == 'CPM'

    ps = ['No Grade', 'Fail', 'Check Minus', 'Check', 'Check Plus']
    ranges = [1.0, 2.0, 2.5]
    assert determine_grade(ps, ranges, 1) == 'Check Minus'
