import csv
import os
import random
import subprocess

# given a csv with one column for email, one column for the choice of each
# lab, and one column for an override, allocates students to those labs
# currently assumes finalresp.csv and 4 labs

labc = 4
hardcap = 19

def get_rand_line(lines, choice_count):
    ls = []
    for line in lines:
        makeable = labc - line.count("I can't make this lab")
        if makeable != choice_count:
            continue

        ls.append(line)

    if not ls:
        return None
    else:
        return random.choice(ls)

f = open('finalresp.csv')
next(f) # get rid of header
lines = list(csv.reader(f))
olines = len(lines)
labs = [set() for i in range(labc)]
getsint = lambda s: int(s.split(' ')[1])
for line in lines:
    if line[-1] != '':
        ln = getsint(line[-1]) - 1
        labs[ln].add(line[0])
        line.append('DONE')

badcount = 0
for line in lines:
    found = False
    for v in line:
        if 'Choice' in v:
            found = True
            break
    if not found:
        badcount += 1
        line.append('DONE')

if badcount:
    print '%s students said they can\'t make any lab' % badcount

assert hardcap >= ((olines - badcount) / labc) + 1, 'invalid hardcap'
lines = filter(lambda l: l[-1] != 'DONE', lines)

done = False
ccount = 1
while lines:
    if ccount > labc:
        print labs, map(len, labs)
        for line in lines:
            print line
        raise Exception('Didn\'t work, sorry :(')
    done = True
    for line in lines:
        if line[-1] != 'DONE':
            done = False
            break

    line = get_rand_line(lines, ccount)
    if line is None:
        ccount += 1
        continue

    for choice in range(labc):
        done = False
        clevel = 'Choice %s' % (choice + 1)
        found = False
        for i, x in enumerate(line):
            if x == clevel:
                found = True
                break

        if found:
            if len(labs[i - 1]) < hardcap:
                done = True
                labs[i - 1].add(line[0])
                line.append('DONE')
                break

    if not done:
        print 'Student does not fit in any lab'
    lines = filter(lambda l: l[-1] != 'DONE', lines)

f = []
for lab in labs:
    for i in lab:
        f.append(i)

for i, lab in enumerate(labs):
    lab_session_name = 'l%s.txt' % (i + 1)
    for x in range(1, 13):
        folder = 'lab%s' % str(x).zfill(2)
        rpath = os.path.join(folder, 'l%s-roster.txt' % (i + 1))
        with open(rpath, 'a') as f:
            for student in lab:
                cmd = ['/course/cs0111/tabin/email-to-login', student]
                login = subprocess.check_output(cmd).strip()
                f.write('%s\n' % login)

