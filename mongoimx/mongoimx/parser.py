import re


def parse_aux(tuples):
    dict_file = {}
    for t in tuples:
        m = re.match(r'^#(.*)', t[0])
        if m:
            key = m[1].lower()
        else:
            key = t[0].lower()
        if re.search(r'path|file|start time|finish time', key):
            value = t[1]
        else:
            numbers = re.findall(r'-?\d+\.?\d*', t[1])
            if numbers == []:
                value = t[1]
            else:
                numbers = [float(s) for s in numbers]
            if len(numbers) == 1:
                value = numbers[0]
            elif len(numbers) > 1:
                value = {'x': numbers[0], 'y': numbers[1]}
        dict_file[key] = value
    return dict_file

def parser_sample(path):
    with open(path) as file:
        file_string = file.read()
    list_s = re.split('\n', file_string)

    i = 0
    regex = re.compile(r'SAMPLE MOTORS')
    for l in list_s:
        if regex.search(l):
            idx_motor_s = i
            break
        i += 1
    i = 0
    for l in list_s[idx_motor_s:]:
        if l == '':
            idx_motor_f = i
            break
        i += 1

    list_motor = list_s[idx_motor_s:idx_motor_s + idx_motor_f]
    list_sample = list_s[0:idx_motor_s]
    list_sample.extend(list_s[idx_motor_s + idx_motor_f:])

    regex = re.compile(r'(.*) [=|-] (.*).*')
    tuples_sample = [(m.group(1), m.group(2)) for l in list_sample for m in [regex.search(l)] if m]
    tuples_motor = [(m.group(1), m.group(2)) for l in list_motor for m in [regex.search(l)] if m]

    dict_file = parse_aux(tuples_sample)
    dict_motor = parse_aux(tuples_motor)
    dict_file['motor positions'] = dict_motor

    return dict_file

def parser_RAfT(path):
    with open(path) as file:
        file_string = file.read()
    list_s = re.split('\n', file_string)
    regex = re.compile(r'(.*) = (.*).*')
    tuples_sample = [(m.group(1), m.group(2)) for l in list_s for m in [regex.search(l)] if m]

    return parse_aux(tuples_sample)
