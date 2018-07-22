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

    # assert len(ranges) == len(possibilities) - 2, \
    #     " key %s doesn't have enough options" % (self.mini_name, key)

    # the ranges needs to have the grade required to get the third item in
    # possibilities, the grade required for the fourth, ... (so first two
    # are not important)
    assert isinstance(score, (int, float))
    if score == None: # no grade
        return possibilities[0]
    
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
