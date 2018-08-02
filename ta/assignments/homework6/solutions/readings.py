from datetime import date, datetime

def Reading(type : str, when : datetime, level : float, location : str):
    """Creates a Reading with four components"""
    return {'type': type,         # what kind of reading (ozone, so2, etc)
            'when': when,         # what date was it taken
            'level': level,       # the numeric reading
            'location': location} # where was the reading taken?

ozone_data = []
so2_data = []

# function used to sort these lists
sort_func = lambda reading: reading['when']

def register_data(reading_list : list):
    for reading in reading_list:
        if reading['type'].lower() == 'ozone':
            ozone_data.append(reading)
        elif reading['type'].lower() == 'so2':
            so2_data.append(reading)
        else:
            inv_type = str(reading['type'])
            raise ValueError('Got reading with invalid type ' + inv_type)

    ozone_data.sort(key=sort_func) # sort from oldest to newest
    ozone_data.reverse() # newest to oldest
    so2_data.sort(key=sort_func)
    so2_data.reverse()

def readings_after(cutoff : datetime, reading_list : list):
    result = []
    for reading in reading_list:
        if reading['when'] >= cutoff:
            result.append(reading)
        else:
            return result            

    return result

so2_threshold = 0.14
ozone_threshold = 0.085

def print_alerts(reading_list : list):
    for reading in reading_list:
        if reading['type'] == 'so2':
            if reading['level'] > so2_threshold:
                base = "Alert for " + reading['location'] + " on "
                print(base + str(reading['when']))
        elif reading['type'] == 'ozone':
            if reading['level'] > ozone_threshold:
                base = "Alert for " + reading['location'] + " on "
                print(base + str(reading['when']))
        else:
            inv_type = str(reading['type'])
            raise ValueError('Got reading with invalid type ' + inv_type)


houston_raw = [[2016, 1, 6, "ozone", "1.0"],
               [2016, 1, 7, "so2", "0.07"],
               [2016, 1, 8, "so2", "0.15"],
               [2016, 1, 2, "ozone", "0.08"]]


def convert_data(array : list, location : str):
    results = []
    for line in array:
        reading = Reading(line[3], date(line[0],
                          line[1], line[2]), float(line[4]), location)
        results.append(reading)

    return results

