#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" HTTP Proxy logging request and responses

"""

import sys
try:
    import argparse
except:
    print "python-argparse is needed"
    sys.exit(1)

import module
from modules import *

def get_parser():
    parser = argparse.ArgumentParser(description="HTTP logging python proxy")
    parser.add_argument("-b","--bind",metavar="IP",default="127.0.0.1",help="Address to bind to")
    parser.add_argument("-p","--port",metavar="PORT",default="8080",type=int,help="Port to bind to")
    return parser

def main():
    """ Entry Point Program """
    parser = get_parser()
    module.Module.main(parser)
    return 0

if __name__ == "__main__":
   sys.exit(main())
