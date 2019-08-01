import sys
import json
import os

if len(sys.argv) != 3:
    print('Usage: python print_results.py <pyret | python> <respath>')

if sys.argv[1] == 'pyret':
    r = os.path.join(sys.argv[2], 'results.json')
    if not os.path.exists(r):
        print('output path does not exist')
        sys.exit(1)

    with open(r) as f:
        data = json.load(f)

    try:
        blocks = data['result']['Ok']
        for block in blocks:
            pass_count = 0
            test_count = 0
            for test in block['tests']:
                if test['passed']:
                    pass_count += 1

                test_count += 1

            print('Block %s: %s/%s tests passed.' % (block['name'],
                                                     pass_count,
                                                     test_count))
    except KeyError:
        print('TEST FORMATTING FAILED')

    print('')
    print('Full results:')
    print(json.dumps(data, indent=2, sort_keys=True))
elif sys.argv[1] == 'python':
    print('No formatting for python results implemented')
    print('See /tabin/print_results.py')
