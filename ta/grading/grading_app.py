import os
import traceback
import sys
import random
import json
import getpass
import argparse
from importlib import reload
from subprocess import Popen, PIPE, STDOUT
from flask import (Flask, session, redirect, url_for,
                   request, render_template)
from flask_assets import Environment, Bundle
from functools import wraps
from passlib.hash import sha256_crypt
from typing import Callable, List, Tuple, Any, NewType, Dict, Optional
from classes import (started_asgns, Assignment, ta_path, hta_path, User, 
                     all_asgns, rubric_base_path, locked_file, json_edit,
                     rubric_schema_path, loaded_rubric_check, asgn_data, BASE_PATH)
from course_customization import full_asgn_name_to_dirname as fatd

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
temp_filename = 'userupdater.py'
assets = Environment(app)
assets.url = app.static_url_path

scss = Bundle('sass/rubric-edit.scss', filters='pyscss', output='gen/rubric-edit.css')
assets.register('scss_rubric_edit', scss)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# i have no idea what this is for but i just button mashed
# (not sure if/how this can be used to hack the program)
app.secret_key = '815tu28g78h8934tgju2893t0j83u2tfjt'

# this dictionary will be used to track what the user is doing;
# which assignment, question, and handin they are working on.
# it's reset if you edit grading_app.py or classes.py while grading
# so you need to refresh the page
# todo: make this better. a lot better. if it's a problem.
workflow = {'asgns': started_asgns()}

# get logged in username
username = getpass.getuser()
user = User(username)
if (user.hta or username == 'eberkowi') and args.user is not None:
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
                           asgns=workflow['asgns'],
                           user=user.uname)


# load an assignment
@app.route('/load_asgn')
@is_logged_in
def load_asgn():
    asgn_key = request.args['asgn']
    found = False
    for asgn in workflow['asgns']:
        if asgn.full_name == asgn_key:
            workflow['assignment'] = asgn
            found = True
            break

    if not found:
        return json.dumps("None")

    if not workflow['assignment'].loaded:
        workflow['assignment'].load()

    lst = [f'Question {q._qnumb}' for q in asgn.questions]
    return json.dumps(lst)


@app.route('/load_prob')
@is_logged_in
def load_prob():
    try:
        q_ndx = int(request.args['prob']) - 1
    except IndexError:
        # received something that wasnt a question index, like the
        # default "Select Problem" option
        raise
        # return json.dumps("None")
    except ValueError:
        return json.dumps("None")
    else:
        asgn = workflow['assignment']
        assert asgn.started, 'grading unstarted assignment %s' % asgn.full_name
        question = asgn.get_question(q_ndx)
        workflow['question'] = question
        d = question.html_data(user)
        return json.dumps(d)


@app.route('/extract_handin')
@is_logged_in
def extract_handin():
    if 'handin_login' in request.args:
        asgn = workflow['assignment']
        if not user.hta and asgn.anonymous:
            return "permission error"
        else:
            ident = asgn.login_to_id(request.args['handin_login'])
            handin = workflow['question'].get_handin_by_id(ident)
    else:
        handin = workflow['question'].get_random_handin(user)

    if handin is None:
        # keep old handin loaded
        return json.dumps("None")
    else:
        handin.start_grading(user.uname)
        workflow['handin'] = handin
        return json.dumps(handin.get_rubric_data())


@app.route('/load_handin', methods=['GET'])
@is_logged_in
def load_handin():
    sid = int(request.args['sid'])
    handin = workflow['question'].get_handin_by_id(sid)
    workflow['handin'] = handin
    return json.dumps(handin.get_rubric_data())


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
    print('saving')
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to unextract inactive handin'

    data = json.loads(request.args['formData'])
    comments = json.loads(request.args['comments'])
    emoji = json.loads(request.args['emoji'])
    workflow['handin'].save_data(data, comments, emoji)
    return 'true'


@app.route('/add_global_comment', methods=['GET'])
@is_logged_in
def add_global_comment():
    print('hi')
    category = request.args['category']
    if category == '':
        category = None

    comment = request.args['comment']
    if workflow['question'].add_ungiven_comment(category, comment):
        print('no')
        return 'added'
    else:
        print('yes')
        return 'not added'


# handin complete; don't save it though, that should be done separately
@app.route('/complete_handin')
@is_logged_in
def complete_handin():
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to unextract inactive handin'

    return json.dumps(workflow['handin'].set_complete())


@app.route('/view_code')
@is_logged_in
def view_code():
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to view student code of inactive handin'
    code = workflow['handin'].get_code(with_tests=False)
    t_code = workflow['handin'].get_code(with_tests=True)
    code_dir = workflow['handin'].handin_path
    return render_template('view_code.html', code=code, code_with_tests=t_code,
                           code_dir=code_dir)


@app.route('/run_test')
@is_logged_in
def run_test():
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to preview report of inactive handin'
    res = workflow['handin'].run_test()
    return render_template('testsuite.html', results=res)
    return json.dumps(workflow['handin'].run_test())


@app.route('/preview_report')
@is_logged_in
def preview_report():
    ident = request.args['id']
    assert workflow['handin'].id == int(ident), \
        'trying to preview report of inactive handin'
    report = workflow['handin'].generate_report_str()
    return render_template('preview_report.html', report=report)


# handle authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in', False):
        return redirect('/')

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


@is_logged_in
@app.route('/render_rubric')
def rubric():
    return render_template('rubric.html', handin=workflow['handin'])


@app.route('/sandbox')
def sandbox():
    return render_template('sandbox.html')

@app.route('/edit-rubric')
@is_logged_in
def edit_rubric():
    return render_template('edit_rubric.html', asgns=all_asgns())

@app.route('/rubricSchema')
def rubricSchema():
    with locked_file(rubric_schema_path) as f:
        return json.dumps(json.load(f))


@app.route('/load_rubric/<mini_name>/<qn>')
@is_logged_in
def load_rubric(mini_name, qn):
    rubric_path = os.path.join(rubric_base_path, mini_name, f'q{qn}.json')
    if not os.path.exists(rubric_path):
        return 'null'
    else:
        with locked_file(rubric_path) as f:
            rubric = json.load(f)

        started = False
        for asgn in asgn_data['assignments']:
            data = asgn_data['assignments'][asgn]
            if (fatd(asgn) == mini_name and data['grading_started']):
                started = True
                break

        return json.dumps({
                'started': started,
                'rubric': rubric
            })

@app.route('/create_rubric/<mini_name>/<qn>')
@is_logged_in
def create_rubric(mini_name, qn):
    base_path = os.path.join(rubric_base_path, mini_name)
    blank_rubric_path = os.path.join(rubric_base_path, 'blank-rubric.json')
    if not os.path.exists(base_path):
        os.mkdir(base_path)

    rubric_path = os.path.join(base_path, f'q{qn}.json')
    if os.path.exists(rubric_path):
        raise ValueError(f'Rubric already exists for {mini_name} question {qn}')

    with locked_file(blank_rubric_path) as f:
        blank_rubric = json.load(f)

    with locked_file(rubric_path, 'w') as f:
        json.dump(blank_rubric, f, indent=2, sort_keys=True)

    return json.dumps(blank_rubric)

@app.route('/update_rubric/<mini_name>/<qn>', methods=['POST'])
@is_logged_in
def update_rubric(mini_name, qn):
    rubric_path = os.path.join(rubric_base_path, mini_name, f'q{qn}.json')
    rubric = request.json
    try:
        loaded_rubric_check(rubric)
        with locked_file(rubric_path, 'w') as f:
            json.dump(rubric, f, indent=2, sort_keys=True)

        success = True
    except AssertionError as e:
        success = False
        if len(e.args) > 0:
            m = e.args[0]
        else:
            m = 'No message'


    return 'Success' if success else m

@app.route('/check_updater/<mini_name>/<qn>', methods=['POST'])
@is_logged_in
def check_updater(mini_name, qn):
    rubric_path = os.path.join(rubric_base_path, mini_name, f'q{qn}.json')
    assert os.path.exists(rubric_path)
    with locked_file(rubric_path) as f:
        rubric = json.load(f)

    code = request.json['code']
    with locked_file(temp_filename, 'w') as f:
        f.write(code)

    p = Popen([os.path.join(BASE_PATH, 'tabin/mypy'),
               temp_filename], stdout=PIPE, stderr=STDOUT)
    output = p.stdout.read().decode()
    try:
        import userupdater
        reload(userupdater)
    except SyntaxError as e:
        return json.dumps({
                'preview': None,
                'results': f'ERROR: SyntaxError in updater\nLine: {e.lineno}'
            })
    try:
        userupdater.updater(rubric)
    except Exception as e:
        output += "\n\nUPDATER FAILED\nError:\n"
        output += traceback.format_exc()
        print(output)
        return json.dumps({
                'results': output,
                'preview': None
            })
    try:
        loaded_rubric_check(rubric)
        valid_rubric = True
    except AssertionError as e:
        valid_rubric = False
        output = e.args[0]

    if not output and valid_rubric:
        res = {
            'results': 'Good',
            'preview': rubric
        }
    else:
        res = {
            'results': output,
            'preview': None
        }

    return json.dumps(res)

@app.route('/run_updater', methods=['POST'])
@is_logged_in
def run_updater():
    asgn_key = request.json['full_asgn']
    qn = request.json['qn']
    code = request.json['code']
    with locked_file(temp_filename, 'w') as f:
        f.write(code)

    try:
        import userupdater
        reload(userupdater)
    except SyntaxError as e:
        err = f'ERROR: SyntaxError in updater\nLine: {e.lineno}'
        return err

    try:
        q = Assignment(asgn_key).questions[int(qn) - 1]
    except AssertionError as e:
        return f'Assertion failed while loading assignment: {e.args[0]}'
    try:
        q.magic_update(userupdater.updater)
    except AssertionError as e:
        return f'AssertionError in magic_update: {e.args[0]}'
    except Exception as e:
        return f'Exception running updater function: {e}'

    return 'Success'


def get_max_points(cat):
    max_val = 0
    for item in cat['rubric_items']:
        max_val += max(map(lambda opt: opt['point_val'], item['options']))

    return max_val


app.jinja_env.globals.update(get_max_points=get_max_points)


if __name__ == '__main__':
    port = args.port
    runtime_dir = os.path.dirname(os.path.abspath(__file__))
    app.run(host='0.0.0.0', port=port, debug=False)
