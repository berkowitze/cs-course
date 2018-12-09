import os
import sys
import random
import flask
import json
from flask import Flask, session, redirect, url_for, request, render_template
from functools import wraps
from passlib.hash import sha256_crypt
import getpass
import argparse
from typing import Callable, List, Tuple, Any, NewType, Dict, Optional
from classes import started_asgns, Assignment, ta_path, hta_path, User

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', default=6924, type=int,
                    help='Port to run the app on.')
parser.add_argument('-u', '--user', type=str,
                    help='TA to run the app as. HTAs only.')
args = parser.parse_args()

# do not run this directly or file permissions will be messed up
# and you need to be in a virtualenvironment
# either run cs111-grade, or reproduce what is done in that script

# could everything be reorganized into a database? yes.
# is it worth it? up to whoever's reading this. I didn't do it
# because it's annoying to learn how databases work and this is an
# intro course (don't assume TAs/HTAs know how databases work)
# but i also suppose that all these files arent exactly convenient

# set up the web app
app = Flask(__name__)

# i have no idea what this is for but i just button mashed
# (not sure if/how this can be used to hack the program)
app.secret_key = '815tu28g78h8934tgju2893t0j83u2tfjt'

# this dictionary will be used to track what the user is doing;
# which assignment, question, and handin they are working on.
# it's reset if you edit grading_app.py or classes.py while grading
# so you need to refresh the page
# todo: make this better. a lot better. if it's a problem.
workflow = {}

# get logged in username
username = getpass.getuser()
user = User(username)
if user.hta and args.user is not None:
    user = User(args.user)

print(user)

def is_logged_in(f: Callable) -> Callable:
    ''' this decorator ensures that the user is logged in when attempting
    to access a route (except /login) '''
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))

    return wrap

# index page
@app.route('/')
@is_logged_in
def main():
    return render_template('index.html',
                           asgns=started_asgns(),
                           user=user.uname)

# load an assignment
@app.route('/load_asgn')
@is_logged_in
def load_asgn():
    try:
        asgn_key = request.args['asgn']
        workflow['assignment'] = Assignment(asgn_key)
        assert workflow['assignment'].started, \
            'attempting to load unstarted assignment'
    except KeyError: # assignment not found
        return json.dumps("None")
    else: # no exceptions raised
        lst = [f'Question {q+1}' for q in workflow['assignment'].questions]
        return json.dumps(lst)

@app.route('/load_prob')
@is_logged_in
def load_prob():
    try:
        prob_ndx = int(request.args['prob']) - 1
    except:
        # received something that wasnt a question index, like the
        # default "Select Problem" option
        return json.dumps("None")
    else:
        asgn = workflow['assignment']
        assert asgn.started, 'grading unstarted assignment %s' % asgn.full_name
        question = asgn.get_question(prob_ndx)
        workflow['question'] = question
        d = question.html_data(user)
        return json.dumps(d)

@app.route('/extract_handin')
@is_logged_in
def extract_handin():
    if 'handin_login' in request.args:
        asgn = workflow['assignment']
        if user.hta or (not asgn.anonymous):
            ident = asgn.login_to_id(request.args['handin_login'])
            handin = workflow['question'].start_ident_handin(ident, user)
        else:
            return "permission error"
    else:
        handin = workflow['question'].get_random_handin(user)

    if handin is None:
        # keep old handin loaded
        return json.dumps("None")
    else:
        workflow['handin'] = handin
        return json.dumps(handin.get_rubric_data())

@app.route('/load_handin', methods=['GET'])
@is_logged_in
def load_handin():
    sid = int(request.args['sid'])
    workflow['handin'] = workflow['question'].get_handin_by_sid(sid, user)
    return json.dumps(workflow['handin'].get_rubric_data())

@app.route('/flag_handin')
@is_logged_in
def flag_handin():
    flag = json.loads(request.args['flag'])
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to flag inactive handin'
    if flag:
        workflow['handin'].flag(msg=request.args['msg'])
    else:
        workflow['handin'].unflag()

    return json.dumps({'flagged': flag,
                       'id': ident,
                       'problemData': workflow['handin'].get_rubric_data()})

@app.route('/unextract_handin')
@is_logged_in
def unextract_handin():
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to unextract inactive handin'

    workflow['handin'].unextract()
    return str(ident)

@app.route('/save_handin')
@is_logged_in
def save_handin():
    ident = request.args['id']
    data = json.loads(request.args['formData'])
    assert workflow['handin'].id == int(ident), \
        'trying to unextract inactive handin'

    comments = json.loads(request.args['comments'])
    completed = json.loads(request.args['completed'])
    # don't force a completely filled out form unless completing
    result = workflow['handin'].save_data(data, comments, force_complete=completed)
    return json.dumps(result)

@app.route('/add_comment')
@is_logged_in
def add_comment():
    ident = request.args['id']
    app.logger.info(ident)
    assert workflow['handin'].id == int(ident), \
        'trying to unextract inactive handin'

    student_only = json.loads(request.args['student-only'])
    category     = request.args['category']
    comment      = request.args['comment']
    if student_only:
        workflow['handin'].add_comment(category, comment)
    else:
        workflow['question'].add_comment(category, comment)

    return 'true'

# handin complete; don't save it though, that should be done separately
@app.route('/complete_handin')
@is_logged_in
def complete_handin():
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to unextract inactive handin'

    workflow['handin'].set_complete()
    return 'good'

@app.route('/preview_report')
@is_logged_in
def preview_report():
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to preview report of inactive handin'

    return json.dumps(workflow['handin'].generate_report_str())

@app.route('/view_code')
@is_logged_in
def view_code():
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to view student code of inactive handin'
    code = workflow['handin'].get_code()
    code_dir = workflow['handin'].handin_path
    return render_template('view_code.html', code=code, code_dir=code_dir)

@app.route('/run_test')
@is_logged_in
def run_test():
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to preview report of inactive handin'
    return json.dumps(workflow['handin'].run_test())

# handle authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_passwd = request.form['password']
        # user_passwd = request.args['password']
        if sha256_crypt.verify(user_passwd, open('passwd_hash.txt').read()):
            session['logged_in'] = True
            return redirect(url_for('main'))
        else:
            return render_template('login.html', msg='Incorrect password')
    else:
        return render_template('login.html', msg='')

# logout (if you need to for some reason)
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = args.port
    runtime_dir = os.path.dirname(os.path.abspath(__file__))
    app.run(host='0.0.0.0', port=port)

