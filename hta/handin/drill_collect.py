import json
import os
from googleapi import sheets_api
from helpers import timestamp_to_datetime

base = '/course/cs0111'
data_path = os.path.join(base, 'ta', 'drills.json')
if not os.path.exists(data_path):
    raise OSError('drills.json not in ta folder')

class Grade:
    def __init__(self, email, sub_time, points, max_points):
        self.email = email
        self.sub_time = sub_time
        self.points = points
        self.grade = float(points) / max_points * 100.0

    def __repr__(self):
        return 'Grade(email=%s, grade=%.2f)' % (self.email, self.grade)

drills = json.load(open(data_path))

service = sheets_api()
sss = service.spreadsheets().values()
overall = {}
for i, drill in enumerate(drills):
    if not drill['grading_complete']:
        continue

    ssid = drill['spreadsheet_id']
    max_points = drill['max_score']
    if 'last_col' in drill:
        col = drill['last_col']
    else:
        col = 'K' # go to column L by default (9 questions)

    res = sss.get(spreadsheetId=ssid, range='A2:%s' % col).execute()
    if 'values' not in res:
        # no lines in Google Sheet
        import sys
        if len(sys.argv) < 2:
            e = "No handins for D.D. %s; run with -o flag to continue anyway"
            raise ValueError(e % i)
        else:
            if sys.argv[1] == '-o':
                continue
    else:
        vals = res['values']

    grades = {}
    for row in vals:
        em = row[1]
        sub_time = timestamp_to_datetime(row[0])

        vs = map(int, row[2].split(' / '))
        points = vs[0]
        assert max_points == vs[1], \
            'json max points does not match quiz max points'

        cgrade = Grade(em, sub_time, points, max_points)
        if em in grades:
            if grades[em].grade < cgrade.grade:
                grades[em] = cgrade
        else:
            grades[em] = cgrade

    for em in grades:
        if em in overall:
            overall[em][i] = grades[em]
        else:
            overall[em]    = {}
            overall[em][i] = grades[em]

for em in overall:
    for i in range(len(drills)):
        if i not in overall[em]:
            overall[em][i] = None

print overall
