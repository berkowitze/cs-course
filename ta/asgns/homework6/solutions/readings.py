from datetime import date, datetime
from testlight import test

def Reading(type : str, when : datetime, level : float, location : str):
    ''' Creates a Reading with four components
    (type must be "ozone" or "so2" '''
    return {'type': type,         # what kind of reading (ozone, so2, etc)
            'when': when,         # what date was it taken
            'level': level,       # the numeric reading
            'location': location} # where was the reading taken?

r_ex_1 = Reading('ozone', date(2018, 5, 17), 0.086, 'Providence')
r_ex_2 = Reading('ozone', date(2018, 6, 12), 0.084, 'Providence')
r_ex_3 = Reading('so2', date(2018, 4, 9), 0.15, 'Houston')

ex_list = [r_ex_1, r_ex_2, r_ex_3]

## QUESTION 1 ##
ozone_data = []
so2_data = []


## QUESTION 2 ##
def sort_func(reading : dict):
    ''' return the metric by which a reading can be sorted (in this case,
    the date of the reading) '''
    return reading['when']

def test_sort_func():
    test("Testing sort_func", sort_func(r_ex_1), date(2018, 5, 17))

def register_data(reading_list : list):
    for reading in reading_list:
        if reading['type'].lower() == 'ozone':
            ozone_data.append(reading)
        elif reading['type'].lower() == 'so2':
            so2_data.append(reading)
        else: # we did not expect you to do this else catch
            inv_type = str(reading['type'])
            raise ValueError('Got reading with invalid type ' + inv_type)

    ozone_data.sort(key=sort_func) # sort from oldest to newest
    ozone_data.reverse() # newest to oldest
    so2_data.sort(key=sort_func)
    so2_data.reverse()

def test_register_data():
    # these two lines get access to the ozone_data and so2_data
    # variables defined at the top of the file
    global ozone_data
    global so2_data
    register_data([])
    test("testing register_data empty list 1", ozone_data, [])
    test("testing register_data empty list 2", so2_data, [])

    # reset for next test
    ozone_data = []
    so2_data = []

    register_data([r_ex_1])
    # test that the reading was appended to ozone_data and not so2_data
    test("simple register_data test 1", ozone_data, [r_ex_1])
    test("simple register_data test 2", so2_data, [])

    # reset for next test
    ozone_data = []
    so2_data = []
    register_data(ex_list)
    # ex2 should come before ex1 since it is more recent
    test("advanced register_data test 1", ozone_data, [r_ex_2, r_ex_1])
    test("advanced register_data test 1", so2_data, [r_ex_3])

def readings_after(cutoff : datetime, reading_list : list):
    ''' inputs :
          `cutoff` : a datetime
          `reading_list` : a list of Readings (dicts), sorted from most
                           recent to oldest/least recent
        output :
          a list of Reading that occured more recently than the cutoff
          date [for this homework, using < or <= didn't matter]
    '''
    result = []
    for reading in reading_list:
        if reading['when'] < cutoff:
            return result # we're earlier than the cutoff, so stop looking...
        else:
            result.append(reading)

    return result

def test_readings_after():
    test("readings_after empty test",
         readings_after(date(2018, 5, 12), []), [])
    test("readings_after all after cutoff",
         readings_after(date(2016, 2, 2), [r_ex_2, r_ex_1, r_ex_3]),
         [r_ex_2, r_ex_1, r_ex_3])
    test("readings_after none after cutoff",
         readings_after(date(2019, 2, 2), [r_ex_2, r_ex_1, r_ex_3]),
         [])
    test("readings_after two after cutoff",
         readings_after(date(2018, 4, 10), [r_ex_2, r_ex_1, r_ex_3]),
         [r_ex_2, r_ex_1])

so2_threshold = 0.14
ozone_threshold = 0.085

def print_alerts(reading_list : list):
    ''' given a list of readings, print out a warning for each reading
    if the level of SO2 or Ozone from that reading is above the respective
    threshold (defined above). No output. '''
    for reading in reading_list:
        # set up a base string, no need to use it though
        # (this is computationally cheap and convenient later)
        ## wrapped in parens to allow multiple lines
        alt = ("Alert for " + reading['location'] + 
              " on " + str(reading['when']))

        # determine whether or not to print an alert
        if reading['type'] == 'so2':
            alert = (reading['level'] > so2_threshold)
        elif reading['type'] == 'ozone':
            alert = (reading['level'] > ozone_threshold)
        else:
            inv_type = str(reading['type'])
            raise ValueError('Got reading with invalid type ' + inv_type)

        if alert:
            print(alt)

# cannot write tests for this (easily), if you're curious how you'd test
# this without changing the functionality, send me an email or a piazza post
# (I had to test your homeworks somehow...)

# that means you have to test it visually
# see below

def convert_data(array : list, location : str):
    ''' given a list of lists, where each sublist has this format:
          [year (int), month (int), day (int),
           reading-type (str), reading-level (convertable to float)]
        and a location (str), convert_data produces a list of Result
        dictionaries, with values converted appropriately to datetimes,
        floats, etc. '''
    results = []
    for line in array:
        reading = Reading(line[3],                         # type
                          date(line[0], line[1], line[2]), # when
                          float(line[4]),                  # level
                          location)                        # location
        results.append(reading)

    return results

def test_convert_data():
    # example of flat data
    houston_raw = [[2016, 1, 6, "ozone", "1.0"],
                   [2016, 1, 7, "so2", "0.07"],
                   [2016, 1, 8, "so2", "0.15"],
                   [2016, 1, 2, "ozone", "0.08"]]

    houston_readings = [Reading("ozone", date(2016, 1, 6), 1.0, "Houston"),
                        Reading("so2",   date(2016, 1, 7), 0.07, "Houston"),
                        Reading("so2",   date(2016, 1, 8), 0.15, "Houston"),
                        Reading("ozone", date(2016, 1, 2), 0.08, "Houston")]
    # the \' tells Python not to end the string "Doesn't matter"
    # due to the apostrophe
    test('convert_data(empty)', convert_data([], 'Doesn\'t matter'), [])
    test('convert_data(houston_raw data)',
         convert_data(houston_raw, 'Houston'),
         houston_readings)

if __name__ == '__main__':
    test_sort_func()
    test_register_data()
    test_readings_after()
    print_alerts([]) # should print nothing
    print_alerts(ex_list) # should print alert for 5/17 and 4/9
    test_convert_data()