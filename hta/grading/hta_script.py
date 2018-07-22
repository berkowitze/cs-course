# TODO:
# load list of assignments
# they can be:
#   unavailable
#   available, still collecting
#   available, not collecting
#   grading unstarted (and unavailable)
#   grading started
#   grading quase-complete (only flagged remain)
#   grading complete, emails unsent
#   grading complete, emails sent, regrades open
#   grading complete, emails sent, regrades not open, regrades incomplete
#   grading complete, emails sent, regrades not open, regrades complete

# for each assignment, can change to a different stage. advanced: some
# options unavailable depending on state, or at least a warning if say
# you try to make an assignment start grading if regrading is already open.
# also give option to reset grading for assignment with override
# override/confirm function
def override():
    print 'Confirm Override? [y/n/ctrl-c to exit]'
    try:
        a = raw_input('> ')
    except KeyboardInterrupt:
        print '\nQuitting...'
        import sys
        sys.exit(0)
    
    if a.lower() == 'y':
        print 'Override confirmed'
        return True
    else:
        print 'No override given'
        return False

override()

# make sure file permissions are set correctly
# make sure all rubrics are valid
# make sure all grades paths are valid
# update list of students (maybe this should be a crontab)



