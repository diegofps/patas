#!/usr/bin/env python3

import time
import sys


def main(args):
    
    p1 = float(args[0])
    p2 = float(args[1])
    p3 = float(args[2])

    # time.sleep(1)

    print(f"Score: {p1*p2*p3}")


main(sys.argv[1:])

