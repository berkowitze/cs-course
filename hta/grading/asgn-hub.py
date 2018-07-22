import json
import os
from hta_helpers import determine_grade
from hta_classes import HTA_Assignment

def get_opt(prompt, options, first=True):
    if first:
        for i, opt in enumerate(options):
            print '%s. %s' % (i + 1, opt)

    print prompt
    choice = raw_input('> ')
    try:
        numb_choice = int(choice) - 1
        if numb_choice in range(len(options)):
            return numb_choice
        else:
            print 'Invalid input...'
            return get_opt(prompt, options, first=False)
    except ValueError:
        print 'Enter a number...'
        return get_opt(prompt, options, first=False)

data_path = '/course/cs0050/ta/assignments.json'
with open(data_path, 'r') as f: # no need for file lock when reading
    data = json.load(f)

Asgns = []
for key in sorted(data['assignments'].keys()):
    Asgns.append(HTA_Assignment(key))

Asgn = Asgns[get_opt('Which assignment are you working on?',
                     map(lambda a: a.full_name, Asgns))]

print Asgn.status()


