import csv

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

def green(text):
    return '\033[32m%s\033[0m' % text

def red(text):
    return '\033[31m%s\033[0m' % text

def yellow(text):
    return '\033[33m%s\033[0m' % text

if __name__ == '__main__':
    print is_blacklisted('eberkowi', 'ncheng2', '/course/cs0111/ta/t-s-blocklist.txt')
