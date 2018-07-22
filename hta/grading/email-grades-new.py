import yagmail, os
from helpers import *
import sys

def immediate_subdirs(a_dir):
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]

yag = yagmail.SMTP('elias_berkowitz@brown.edu')
base = '/course/cs0050/hta/grades'
hw = 'homework4'

students = immediate_subdirs(base)
for student in students:
    student_path = os.path.join(base, student)
    if not os.path.isdir(student_path):
        print 'nonstudent file %s in students directory' % student
        continue

    grade_path = os.path.join(student_path, hw, 'report.txt')
    if not os.path.exists(grade_path):
        print 'grade for student %s does not exist' % student
        raise

    student_email = login_to_email(student)
    grade_content = open(grade_path).read()
    email_content = '<pre>%s</pre>' % grade_content
    yag.send(to=student_email,
             subject='Homework 4 Grade Report',
             contents=[email_content])
