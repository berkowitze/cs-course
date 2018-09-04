import sys
import json
import os

if len(sys.argv) != 3:
    print 'Usage: python print_results.py <pyret | python> <respath>'

if sys.argv[1] == 'pyret':
    r = os.path.join(sys.argv[2], 'results.json')
    if not os.path.exists(r):
        print 'output path does not exist'
        sys.exit(1)

    with open(r) as f:
        data = json.load(f)

    print json.dumps(data, indent=2, sort_keys=True)
