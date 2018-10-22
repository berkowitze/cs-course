import csv
import os

# must be run with a python installation with tabulate (i.e. ta/grading/venv)

def is_blacklisted(u1, u2, path):
    lines = []
    with open(path) as f:
        for line in f:
            lines.append(map(str.strip, line.split(',')))
    
    for line in lines:
        if ((line[0] == u1 and line[1] == u2) or
            (line[0] == u2 and line[1] == u1)):
            return True

    return False

def get_login_from_list(n, required=True):
    ''' using the student list, prompt user for n logins. If not required, 
    will prompt for up to n '''
    import tabulate
    ls = set()
    b = '/course/cs0111'
    s_path = os.path.join(b, 'ta/groups', 'students.csv')
    with open(s_path) as f:
        lines = list(csv.reader(f))
    
    for i in range(len(lines)):
        lines[i].insert(0, i + 1)

    print tabulate.tabulate(lines, headers=('#', 'Login', 'Email', 'Name'))
    if required:
        print('ctrl-c will exit script')
    else:
        print('ctrl-c will stop collecting logins')

    while len(ls) < n:
        try:
            res = raw_input('Enter the # of the student: ')
            ndx = int(res)
            login = lines[ndx - 1][1]
            ls.add(login)
        except KeyboardInterrupt:
            if required:
                raise
            else:
                return ls

    return ls


def green(text):
    return '\033[32m%s\033[0m' % text

def red(text):
    return '\033[31m%s\033[0m' % text

def yellow(text):
    return '\033[33m%s\033[0m' % text

if __name__ == '__main__':
    print is_blacklisted('eberkowi', 'ncheng2', '/course/cs0111/ta/t-s-blocklist.txt')
