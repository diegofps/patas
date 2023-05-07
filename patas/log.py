import sys

LOG_LEVEL = 2

def debug(*args):
    if LOG_LEVEL <= 0:
        print("DEBUG:", *args)

def info(*args):
    if LOG_LEVEL <= 1:
        print("INFO:", *args)

def warn(*args):
    if LOG_LEVEL <= 2:
        print("WARN:", *args)

def error(*args):
    if LOG_LEVEL <= 3:
        print("ERROR:", *args)
    sys.exit(1)
