#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict

try:
    import argparse
except:
    print "python-argparse is needed"
    sys.exit(1)

class ModuleRegister(object):
    registry = defaultdict(dict)

    @classmethod
    def register(cls,obj,key="__name__"):
        cls.registry[cls.__name__][getattr(obj,key)] = obj
        return obj

    @classmethod
    def get(cls, name, default=None):
        return cls.registry[cls.__name__].get(name, default)

    @classmethod
    def itervalues(cls):
        return cls.registry[cls.__name__].itervalues()

class Module(object):
    _desc_ = "N/A"

    @staticmethod
    def register(f):
        return ModuleRegister.register(f,key="__name__")

    @classmethod
    def create_arg_parser(cls):
        parser = argparse.ArgumentParser(description="HTTP logging python proxy")
        parser.add_argument("-b","--bind",metavar="IP",default="127.0.0.1",help="Address to bind to")
        parser.add_argument("-p","--port",metavar="PORT",default="8080",type=int,help="Port to bind to")

        subparsers = parser.add_subparsers(dest="module_name",help="Modules")
        for module in ModuleRegister.itervalues():
            p = subparsers.add_parser(module.__name__,help=module._desc_)
            module.create_arg_subparser(p)

        return parser

    @classmethod
    def create_arg_subparser(cls,parser):
        pass

    @classmethod
    def main(cls):
        parser = cls.create_arg_parser()
        args = parser.parse_args()

        module = ModuleRegister.get(args.module_name)
        m = module(args)

        m.run()

    def __init__(self,args):
        pass
