import os
import sys
from datetime import date, datetime
import random
from io import StringIO
import numpy as np

class Capturing(list):
    ''' used for capturing STDOUT (from print statements)
    usage:
        with Capturing() as capture:
            print('hello')
            print('there')
        
        # capture = ["hello", "there"]
    '''
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout # reset standard output

# solution path
fta = '/course/cs0050/ta/assignments/homework6/solutions/readings.py'

def Reading(type : str, when : datetime, level : float, location : str):
    """Creates a Reading with four components"""
    return {'type': type,         # what kind of reading (ozone, so2, etc)
           'when': when,          # what date was it taken
           'level': level,        # the numeric reading
           'location': location}  # where was the reading taken?


if len(sys.argv) != 2:
    raise IndexError('Test must be called with file as argument')

f = sys.argv[1]
if not os.path.exists(f):
    raise OSError('TA Test called on file that does not exist.')

with open(f) as fo:
    for i, line in enumerate(fo):
        if len(line) > 80:
            print('Student has code over 80 characters (line %s)' % i)

try:
    # see https://stackoverflow.com/questions/67631
    import importlib.util
    spec = importlib.util.spec_from_file_location("student_module", f)
    scode = importlib.util.module_from_spec(spec)
    with Capturing() as output:
        # load students code and capture any stdout that results from
        # executing their file
        msg = '(Output from student code captured.'
        msg += ' run with --full as third argument to see code output)'
        print(msg)
        spec.loader.exec_module(scode)
    
    print(output)
    output = []
except SyntaxError:
    print('Student has syntax error')
    raise
except:
    print('Student has error that stops code from running.')
    raise

spec = importlib.util.spec_from_file_location("ta_module", fta)
tacode = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tacode)

#### TESTS GO HERE
svars = dir(scode) # get all definitions in students' code
if 'Reading' not in svars:
    print('Student did not copy Reading func')
else:
    if not callable(scode.Reading):
        print('Student overwrote Reading func')

if 'ozone_data' not in svars:
    print('No ozone_data list')
    has_ozone = False
else:
    if not isinstance(scode.ozone_data, list):
        has_ozone = False
        print('Student code ozone_data is not list, got %s' % scode.ozone_data)
    else:
        has_ozone = True


if 'so2_data' not in svars:
    print('No so2_data list')
    has_so2 = False
else:
    if not isinstance(scode.so2_data, list):
        print('Student code so2_data is not list, got %s' % scode.so2_data)
        has_so2 = False
    else:
        has_so2 = True

if has_so2 and has_ozone:
    setup = True
    print('Question 1 passed.')
else:
    setup = False
    print('Must grade by hand...')
    sys.exit(1)

# generate a bunch of random readings
rs = []
samples = 500
choices = list(range(2000, 2000 + samples + 10)) # adding 10 just in case
for i in range(samples):
    TYPE = random.choice(['ozone', 'so2'])
    y = random.choice(choices)
    choices.remove(y)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    DATE = date(y, m, d)
    if TYPE == 'ozone':
        LEVEL = np.random.normal(0.08, scale=0.01)
    else:
        LEVEL = np.random.normal(0.1, scale=0.08)

    LEVEL = round(LEVEL, 5)
    LOCATION = random.choice(['Houston', 'Boston', 'Providence'])
    rs.append(Reading(TYPE, DATE, LEVEL, LOCATION))

if 'register_data' not in svars:
    print('No function register_data.')
    q2 = False
else:
    annotations = scode.register_data.__annotations__
    if annotations == {} or (list not in annotations.values()):
        print('No or invalid annotations on register_data')
    if scode.register_data.__doc__ is None:
        print('No docstring for register_data')

    scode.ozone_data = []
    scode.so2_data = []
    tacode.ozone_data = []
    tacode.so2_data = []
    tacode.register_data(rs.copy())
    try:
        scode.register_data(rs.copy())
    except:
        print('Student Code errored on register_data')
        raise

    if scode.ozone_data == tacode.ozone_data:
        ozone_pass = True
    else:
        ozone_pass = False
        try:
            sorted_version = list(sorted(scode.ozone_data,
                                         key=lambda r: r['when'], reverse=True))
        except KeyError:
            print('ozone_data not a list of readings')
        if sorted_version == tacode.ozone_data:
            print('register_data: not sorted at all or sorted incorrectly (ozone_data)')
        elif list(reversed(scode.ozone_data)) == tacode.ozone_data:
            print('register_data: student code in reverse order')
        else:
            print(sorted_version[0], tacode.ozone_data[0])
            print('register_data: ozone_data not registered correctly')


    if scode.so2_data == tacode.so2_data:
        so2_pass = True
    else:
        so2_pass = False
        try:
            sorted_version = list(sorted(scode.so2_data,
                                         key=lambda r: r['when'], reverse=True))
        except KeyError:
            print('so2_data not a list of readings')
            raise
        if sorted_version == tacode.so2_data:
            print('register_data: not sorted at all or sorted incorrectly (so2_data)')
        elif list(reversed(scode.so2_data)) == tacode.so2_data:
            print('register_data: student code in reverse order')
        else:
            if (len(scode.so2_data) == len(tacode.so2_data)):
                for d1, d2 in zip(sorted_version, tacode.so2_data):
                    if d1 != d2:
                        print(d1['type'], d2['type'], d1['when'], d2['when'], d1['location'], d2['location'])
            else:
                print("Actually wrong")
            
            print('register_data: so2_data not registered correctly')

    if ozone_pass and so2_pass:
        q2 = True
    else:
        q2 = False

if q2:
    print("Question 2 passed.")
else:
    print("Question 2 failed.")

q3 = False
if 'readings_after' not in svars:
    print('readings_after does not exist')
elif not callable(scode.readings_after):
    print('readings_after not a function')
elif scode.readings_after.__code__.co_argcount != 2:
    print('readings_after does not take in 2 arguments as expected')
else:
    if scode.readings_after.__doc__ == None:
        print('No docstring for readings_after')
    annotations = scode.readings_after.__annotations__
    if annotations == {}:
        print('No annotations on readings_after')
        good_annotations = False
    else:
        if list not in annotations.values():
            print('No list input annotation on readings_after')
            a = False
        else:
            a = True
        if datetime not in annotations.values():
            print('No datetime input annotation on readings_after')
            b = False
        else:
            b = True
        good_annotations = a and b

    if scode.readings_after.__doc__ is None:
        print('No docstring for readings_after')

    ds = map(lambda r: r['when'], rs)
    while True:
        cutoffreading = random.choice(rs)
        cd = cutoffreading['when']
        cutoffdate = date(cd.year, cd.month, cd.day - 1 if cd.day != 1 else cd.day + 1)
        if cutoffdate not in ds:
            break

    srs = sorted(rs, key=lambda r: r['when'], reverse=True)
    if not good_annotations:
        try:
            res = scode.readings_after(cutoffdate, srs)
        except TypeError:
            try:
                res = scode.readings_after(srs, cutoffdate)
            except:
                print("Student code raised error")
                raise
    else:
        import inspect
        args = inspect.getfullargspec(scode.readings_after).args
        inps = []
        for arg in args:
            if annotations[arg] == datetime:
                inps.append(cd)
            else:
                inps.append(srs)

        res = scode.readings_after(*tuple(inps))

    if res == tacode.readings_after(cd, srs):
        q3 = True
    else:
        print(len(res), len(tacode.readings_after(cd, srs)))
        print('Potentially got dates before, not dates after cutoff.')
        q3 = False

if q3:
    print('Question 3 passed.')
else:
    print('Question 3 failed.')


q4 = False
if 'print_alerts' not in svars:
    print('print_alerts does not exist.')
elif not callable(scode.print_alerts):
    print('print_alerts is not a function')
elif scode.print_alerts.__code__.co_argcount != 1:
    print('print_alerts does not take 1 argument')
else:
    annotations = scode.print_alerts.__annotations__
    if annotations == {} or (list not in annotations.values()):
        print('No or invalid annotations on print_alerts')
    if scode.print_alerts.__doc__ is None:
        print('No docstring for print_alerts')

    if 'return' in annotations and annotations['return'] == list:
        print('Student print_alerts returns list (do not deduct)')

    with Capturing() as output:
        tacode.print_alerts(rs)

    tao = output.copy() # ta output

    with Capturing() as output:
        scode.print_alerts(rs)

    sto = output.copy() # student output

    if tao != sto:
        q4 = False
        print('print_alerts output do not match. Got:')
        short_sto = sto if len(sto) < 5 else sto[0:4]
        for o in short_sto:
            print('\t%s' % o)
        if len(sto) >= 5:
            print('...')
        print('Expected:')
        short_tao = tao if len(tao) < 5 else tao[0:4]
        for o in short_tao:
            print('\t%s' % o)

        if len(tao) >= 5:
            print('...')
    else:
        q4 = True

if q4:
    print("Question 4 passed.")
else:
    print("Question 4 failed.")

flat = []
for r in rs:
    d = r['when']
    if r['location'] != 'Providence':
        continue
    else:
        flat.append([d.year, d.month, d.day, r['type'], r['level']])

assert len(flat) > 1, 'Rerun testsuite.'

q5 = False
if 'convert_data' not in svars:
    print('convert_data does not exist.')
elif not callable(scode.convert_data):
    print('convert_data is not a function')
elif scode.convert_data.__code__.co_argcount != 2:
    print('convert_data does not take 1 argument')
else:
    annotations = scode.convert_data.__annotations__
    if annotations == {}:
        print('No annotations on convert_data')
        good_annotations = False
    elif list not in annotations.values() or str not in annotations.values():
        good_annotations = False
        print('Invalid annotations for convert_data')
    else:
        good_annotations = True

    if scode.convert_data.__doc__ is None:
        print('No docstring for convert_data')

    inp1 = (flat, 'Providence')
    inp2 = ('Providence', flat)
    try:
        res = scode.convert_data(*inp1)
    except:
        res = scode.convert_data(*inp2)

    if res == tacode.convert_data(flat, 'Providence'):
        q5 = True

if q5:
    print("Question 5 passed.")
else:
    print("Question 5 failed.")
