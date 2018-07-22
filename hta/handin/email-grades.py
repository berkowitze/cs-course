import yagmail, os
from helpers import *
import sys
def immediate_subdirs(a_dir):
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]

def latest_sub(subs):
    assert len(subs) > 0, 'no submission but directory exists'
    latest_numb = 0
    latest_path = subs[0]
    for sub in subs:
        if not len(sub.split('-')) >= 2:
            print 'invalid named submission directory in %s' % sub

        sub_numb = int(sub.split('-')[0])
        if sub_numb > latest_numb:
            latest_numb = sub_numb
            latest_path = sub

    return latest_path

yag = yagmail.SMTP('elias_berkowitz@brown.edu')
base = '/course/cs0050/hta/handin/students'
hw = 'homework3'

students = immediate_subdirs(base)
for student in students:
    student_path = os.path.join(base, student)
    if not os.path.isdir(student_path):
        print 'nonstudent file %s in students directory' % student
        continue

    asgn_path = os.path.join(student_path, hw)
    submissions = immediate_subdirs(asgn_path)
    last_submission = latest_sub(submissions)
    grade_path = os.path.join(asgn_path, last_submission, 'grade.txt')
    if not os.path.exists(grade_path):
        print 'grade for student %s does not exist' % student
        continue

    student_email = login_to_email(student)
    grade_content = open(grade_path).read()
    prestring = 'Hi %s: below is your grade and comments for homework 3.'
    email_content = '%s<pre>%s</pre>' % (prestring % student, grade_content)
    yag.send(to=student_email,
             subject='Homework 3 Grade Report',
             contents=[email_content])
