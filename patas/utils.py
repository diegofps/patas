from subprocess import Popen, PIPE

import shutil
import shlex
import glob
import sys
import re
import os



class colors:
    RESET="\033[0m"

    RESET     = "\033[0m"

    BRIGHTER  = "\033[1m"
    DARKER    = "\033[2m"
    ITALIC    = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINKING  = "\033[5m"
    REVERSE   = "\033[7m"
    INVISIBLE = "\033[8m"
    CROSSING  = "\033[9m"

    GRAY    = "\033[90m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    PURPLE  = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"

    BOLD_GRAY   = "\033[1;30m"
    BOLD_RED    = "\033[1;31m"
    BOLD_GREEN  = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_BLUE   = "\033[1;34m"
    BOLD_PURPLE = "\033[1;35m"
    BOLD_CYAN   = "\033[1;36m"
    BOLD_WHITE  = "\033[1;37m"

    BG_GRAY   = "\033[40m"
    BG_RED    = "\033[41m"
    BG_GREEN  = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE   = "\033[44m"
    BG_PURPLE = "\033[45m"
    BG_CYAN   = "\033[46m"
    BG_WHITE  = "\033[47m"

    @staticmethod
    def gray(str):
        return colors.GRAY + str + colors.RESET
    
    @staticmethod
    def red(str):
        return colors.RED + str + colors.RESET
    
    @staticmethod
    def green(str):
        return colors.GREEN + str + colors.RESET

    @staticmethod
    def yellow(str):
        return colors.YELLOW + str + colors.RESET
        
    @staticmethod
    def blue(str):
        return colors.BLUE + str + colors.RESET
    
    @staticmethod
    def purple(str):
        return colors.PURPLE + str + colors.RESET
    
    @staticmethod
    def cyan(str):
        return colors.CYAN + str + colors.RESET
    
    @staticmethod
    def white(str):
        return colors.WHITE + str + colors.RESET

    @staticmethod
    def normal(str):
        return colors.RESET + str + colors.RESET


def readlines(master, lines, verbose=False):
    
    o = os.read(master, 10240)

    if verbose:
        os.write(sys.stdout.fileno(), o)

    if not o:
        return 0, 0
    
    last = 0
    i = 0

    linebreak = ord('\n')
    result = []

    while i != len(o):
        if o[i] == linebreak:
            result.append(o[last:i+1])
            last = i + 1
        
        i += 1
    
    result.append(o[last:i])

    start_search = max(len(lines) - 1, 0)

    if lines:
        lines[-1] = lines[-1] + result[0]
        lines.extend(result[1:])
    else:
        lines.extend(result)
    
    return start_search, len(lines)


def quote(str):
    return '"' + re.sub(r'([\'\"\\])', r'\\\1', str) + '"'


def quote_single(str):
    return "'" + re.sub(r'([\'\\])', r'\\\1', str) + "'"


def run(cmds, write=None, read=False, suppressInterruption=False, suppressError=False, verbose=False):
    if type(cmds) is not list:
        cmds = [cmds]
    
    if not cmds:
        return
    
    if verbose:
        print("Executing command:\n" + " | ".join(cmds))

    try:
        if write and read:
            args = shlex.split(cmds[0])
            ps = [Popen(args, stdout=PIPE, stdin=PIPE)]

            for i in range(1, len(cmds)):
                args = shlex.split(cmds[i])
                previous = ps[i-1]
                current = Popen(args, stdout=PIPE, stdin=previous.stdout)
                ps.append(current)

            front = ps[0]
            for line in write:
                front.stdin.write(line.encode())
            front.stdin.close()

            back = ps[-1]
            lines = [line.decode("utf-8") for line in back.stdout]
            status = back.wait()

            if not suppressError and status != 0:
                error("Failed to execute command:\n" + " | ".join(cmds))
            
            return status,lines

        elif write:
            args = shlex.split(cmds[0])

            if len(cmds) == 1:
                ps = [Popen(args, stdin=PIPE)]
            else:
                ps = [Popen(args, stdout=PIPE, stdin=PIPE)]

            final = len(cmds) - 1
            for i in range(1, final):
                args = shlex.split(cmds[i])
                previous = ps[i-1]

                if i + 1 == final:
                    ps.append(Popen(args, stdin=previous.stdout))
                else:
                    ps.append(Popen(args, stdout=PIPE, stdin=previous.stdout))

            front = ps[0]
            for line in write:
                front.stdin.write(line.encode())
            front.stdin.close()

            status = ps[-1].wait()

            if not suppressError and status != 0:
                error("Failed to execute command:\n" + " | ".join(cmds))
            
            return status, None

        elif read:
            args = shlex.split(cmds[0])
            ps = [Popen(args, stdout=PIPE)]

            for i in range(1, len(cmds)):
                args = shlex.split(cmds[i])
                previous = ps[i-1]
                current = Popen(args, stdout=PIPE, stdin=previous.stdout)
                ps.append(current)

            back = ps[-1]
            lines = [line.decode("utf-8") for line in back.stdout]
            status = back.wait()

            if not suppressError and status != 0:
                error("Failed to execute command:\n" + " | ".join(cmds))
            
            return status, lines

        elif len(cmds) == 1:
            status = os.system(cmds[0])

            if not suppressError and status != 0:
                error("Failed to execute command:\n" + " | ".join(cmds))
            
            return status, None
        
        else:
            args = shlex.split(cmds[0])
            ps = [Popen(args, stdout=PIPE)]

            for i in range(1, len(cmds)-1):
                args = shlex.split(cmds[i])
                previous = ps[i-1]
                current = Popen(args, stdout=PIPE, stdin=previous.stdout)
                ps.append(current)

            args = shlex.split(cmds[-1])
            previous = ps[-1]
            current = Popen(args, stdin=previous.stdout)
            ps.append(current)

            status = ps[-1].wait()
            
            if not suppressError and status != 0:
                error("Failed to execute command:\n" + " | ".join(cmds))
            
            return status, None

    except KeyboardInterrupt as e:
        if not suppressInterruption:
            raise e


def abort(*args):
    if args:
        msg = colors.PURPLE + ' '.join([str(x) for x in args]) + colors.RESET
        print(msg, file=sys.stderr)
    exit(1)


def error(*args):
    if args:
        raise PatasError(" ".join(args))
    else:
        raise PatasError()


def critical(*args):
    print(colors.RED + "|CRITICAL| " + " ".join([str(v) for v in args]) + colors.RESET)


def warn(*args):
    print(colors.YELLOW + "|WARNING| " + " ".join([str(v) for v in args]) + colors.RESET)


def info(*args):
    print(colors.GREEN + "|INFO| " + " ".join([str(v) for v in args]) + colors.RESET)


def debug(*args):
    print(colors.CYAN + "|DEBUG| " + " ".join([str(v) for v in args]) + colors.RESET)


def filename(filepath):
    return os.path.splitext(os.path.basename(filepath))[0]


def expand_path(filepath):
    if not filepath:
        return filepath
    
    if filepath.startswith("/"):
        return filepath
    
    if filepath.startswith("./") or filepath.startswith("../"):
        return os.path.abspath(filepath)
    
    if filepath.startswith("~"):
        return os.path.expanduser(filepath)
    
    return os.path.abspath(os.path.join(".", filepath))


class PatasError(Exception):
    def __init__(self, message=None):
        self.message = message


def clean_folder(folderpath):
    
    if os.path.exists(folderpath):
        if os.path.isdir(folderpath):
            for filepath in glob.glob(os.path.join(folderpath, '*')):
                debug("  Removing:", filepath)
                if os.path.isdir(filepath):
                    shutil.rmtree(filepath)
                else:
                    os.remove(filepath)
        else:
            os.remove(folderpath)
    else:
        os.makedirs(folderpath, exist_ok=True)


def human_time(seconds):

    v = seconds

    if v < 60:
        return f"{v} seconds"
    v /= 60

    if v < 60:
        return f"{v} minutes"
    v /= 60

    if v < 24:
        return f"{v} hours"
    v /= 24

    if v < 7:
        return f"{v} days"
    v /= 7

    if v < 52:
        return f"{v} weeks ~ {v / 4.0} months"
    v /= 52

    if v < 100:
        return f"{v} years"
    v /= 100

    if v < 10:
        return f"{v} centuries"
    v /= 10

    return f"{v} milleniums"

def estimate(tasks, workers, seconds):
    
    return human_time(tasks / workers * seconds)
