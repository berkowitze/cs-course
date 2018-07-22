import test
from student_solution import mean, bad_mean, map2

# correct tests for a correct function
test.Expect(mean, [0, 1], 0.5)
test.Within(mean, [5, 3, 2], 3.33, tolerance=0.01)
test.Error(mean, [], 'Cannot take mean of empty list.')
test.Expect(mean, [0], 0)

# correct tests for an incorrect function
test.Expect(bad_mean, [0, 1], 0.5)
test.Within(bad_mean, [5, 3, 2], 3.33, tolerance=0.01)
test.Error(bad_mean, [], 'Cannot take mean of empty list.')
test.Expect(bad_mean, [0], 0)

# incorrect tests
# they all raise errors
# test.Expect(mean, [0, 1], 0.5, 0.2)
# test.Within(mean, [5, 3, 2], 3.33, 0.01)
# test.Error(mean, [], 17)
# test.Expect(mean, 9, 10, 11, 10)

test.Expect(map2, 
            (lambda x, y: x + y,
             [1,2,3],
             [4,5,6]),
            [5, 7, 9])