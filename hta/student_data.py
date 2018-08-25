# functions to get emails and logins of a group
#
# Notes: 
#  - if running from ssh/fastx, make sure to run "kinit" first
# 
# @author zkirsche Aug 2018
# edited by eberkowi Aug 2018
#   - reduced terminal output
#   - reorganized functions to take group names instead of login CSV files

import cgi
import csv
from StringIO import StringIO
import re
import os
import smtplib
import subprocess
import sys

def login_to_email(login):
    '''
    Input: the brown cs login to query
    Output: the brown email, or an error string that the email can't be found
            and a boolaen indicating if the search succeeded
    '''
    try:
        login = login.lower().strip()
        userdata = subprocess.check_output(["ldapsearch", "-Q", "cn=" + login])
        ldap_email = re.search("mail:(.*)", userdata, re.MULTILINE)
        if ldap_email:
            email = ldap_email.group(1).strip()
            return email, True
        else:
            return "Unknown login %s (email HTAs)" % login, False

    except subprocess.CalledProcessError:
        return "Warning: ldap search for %s failed" % login, False

def get_logins_from_group(group_name):
    '''
    Input: a group name (i.e. cs-0111ta)
    Output: A list of the usernames of the members of that group 
    (uses the members command)

    repeated usernames are deleted
    '''
    cmd = ['members', group_name]
    sp = subprocess.Popen(cmd,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    out, err = sp.communicate()
    if out and not err:
        # success
        return out.strip().split(' ')
    elif not out and not err:
        # no members in group
        return []
    else:
        # probably invalid group name
        raise subprocess.CalledProcessError(1, cmd, err)

def get_login_email_zip(group_name, filter_invalids=False):
    '''
    Input: a group name (i.e. cs-0111ta) and a boolean indicating if
    you want to filter invalid username/email pairs
    Output: A set of the (login, email) tuples, one for each member
    of the group (uses the members and ldapsearch commands)
    if filter_invalids = True, filters out usernames that weren't found

    repeated usernames are filtered regardless
    '''
    members = get_logins_from_group(group_name)
    res = list(map(login_to_email, members))
    if filter_invalids:
        out = set()
        for i in range(len(members)):
            if res[i][1]:
                out.add((members[i], res[i][0]))

    else:
        out = set((zip(members, [r[0] for r in res])))

    return list(out)

if __name__ == '__main__':
    import sys
    argv = sys.argv
    if len(argv) != 3:
        print 'Usage: %s <group-name> <output-path.csv>'

    lines = get_login_email_zip(argv[1], filter_invalids=True)
    s = '\n'.join(map(lambda line: ','.join(map(str, line)), lines))
    with open(argv[2], 'w') as f:
        f.write(s)
