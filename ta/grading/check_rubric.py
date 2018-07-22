import sys, json, os

try:
    rubric_path = sys.argv[1]
except IndexError:
    print 'Usage: python check_rubric.py <path-to-rubric.json>'
    sys.exit(0)

if not os.path.exists(rubric_path):
    print 'Path does not exist'
    sys.exit(0)

try:
    rubric = json.load(open(rubric_path))
except ValueError:
    print 'Error parsing JSON file'
    raise
assert '_COMMENTS' in rubric, 'rubric must have _COMMENTS key'
assert isinstance(rubric['_COMMENTS'], list), 'rubric _COMMENTS must be a list'
for itm in rubric['_COMMENTS']:
    # itm = rubric['_COMMENTS'][item]
    assert isinstance(itm, dict)
    assert 'comment' in itm, 'each item in _COMMENTS list must have a comment field'
    assert 'value' in itm, 'each item in _COMMENTS list must have a value field'
    assert itm['value'] == False, \
        'the value field for each item in _COMMENTS must be False by default (comment not given)'

for category in rubric:
    if category == '_COMMENTS':
        continue
    for criterion in rubric[category]:
        crit_keys = criterion.keys()
        assert 'name' in crit_keys, \
               '%s does not have "name" key' % category
        assert 'options' in crit_keys, \
               '%s > "%s" does not have "options" key' % (category, criterion['name'])
        assert 'default' in crit_keys, \
               '%s > "%s" does not have "default" key' % (category, criterion['name'])

print 'Rubric is valid.'