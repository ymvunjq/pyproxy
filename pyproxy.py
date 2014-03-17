#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" HTTP Proxy logging request and responses

"""

import sys
import logging
try:
    import argparse
except:
    print "python-argparse is needed"
    sys.exit(1)

import proxy
import module
from modules import *

def get_parser():
    parser = argparse.ArgumentParser(description="HTTP logging python proxy")
    parser.add_argument("-b","--bind",metavar="IP",default="127.0.0.1",help="Address to bind to")
    parser.add_argument("-p","--port",metavar="PORT",default="8080",type=int,help="Port to bind to")
    parser.add_argument("--debug",metavar="DEBUG_LEVEL",default="info",help="Set debug level for proxy core")
    return parser

def main():
    """ Entry Point Program """
    parser = get_parser()
    parser = module.Module.create_arg_parser(parser)
    args = parser.parse_args()

    proxy.logger.setLevel(getattr(logging,args.debug.upper(),None))

    mod = module.ModuleRegister.get(args.module_name)
    m = mod(args)

    pxy = proxy.Proxy(args.port,args.bind,[m])
    pxy.run()

    return 0

if __name__ == "__main__":
   sys.exit(main())
