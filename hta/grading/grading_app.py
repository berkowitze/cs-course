import os, random, flask, json
from flask import Flask, session, redirect, url_for, \
                  abort, request, render_template, \
                  get_template_attribute
import numpy as np
from functools import wraps
from classes import started_asgns, Assignment, ta_path, hta_path, User
from passlib.hash import sha256_crypt
import getpass

# could everything be reorganized into a database? yes.
# is it worth it? up to whoever's reading this. I didn't do it
# because it's annoying to learn how databases work but all these
# files arent exactly convenient

# todo file locking

# set up the web app
app = Flask(__name__)

# super secure password
# (not sure if/how this can be used to hack the program)
app.secret_key = 'random key'

# this dictionary will be used to track what the user is doing;
# which assignment, question, and handin they are working on.
# it's reset if you edit grading_app.py or classes.py while grading
# so you need to refresh the page
workflow = {}

username = getpass.getuser()
user = User(username)

def is_logged_in(f):
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
    # just make sure no one is making a really malformed request
    assert isinstance(request.args['asgn'], (str, unicode))
    try:
        asgn_key = request.args['asgn']
        workflow['assignment'] = Assignment(asgn_key)
        assert workflow['assignment'].started, \
            'attempting to load unstarted assignment'
    except KeyError:
        return json.dumps("None")
    else: # this is run if no exceptions are raised
        return json.dumps(map(lambda q: 'Question %s' % (q+1),
                          range(len(workflow['assignment'].questions))))

@app.route('/load_prob')
@is_logged_in
def load_prob():
    try:
        prob_ndx = int(request.args['prob']) - 1
    except:
        # sent something that wasnt a question index, like the
        # default "Select Problem" option
        return json.dumps("None")
    else:
        asgn = workflow['assignment']
        asgn.load_questions()
        question = asgn.get_question(prob_ndx)
        workflow['question'] = question
        return json.dumps(question.html_data(user))

@app.route('/extract_handin')
@is_logged_in
def extract_handin():
    handin = workflow['question'].get_random_handin(user)
    workflow['handin'] = handin
    if handin is None:
        return json.dumps("None")
    else:
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
    # just sanity checking, can get rid or add this in other places for security todo
    assert isinstance(comments, dict)
    assert isinstance(completed, bool)
    assert isinstance(data, dict)
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
    port = 6127 # use an obscure port
    runtime_dir = os.path.dirname(os.path.abspath(__file__))

    app.run(port=port, debug=True)

