#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict

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
    def create_arg_parser(cls,parser):
        subparsers = parser.add_subparsers(dest="module_name",help="Modules")
        for module in ModuleRegister.itervalues():
            p = subparsers.add_parser(module.__name__,help=module._desc_)
            module.create_arg_subparser(p)

        return parser

    @classmethod
    def create_arg_subparser(cls,parser):
        pass

    @classmethod
    def main(cls,parser):
        parser = cls.create_arg_parser(parser)
        args = parser.parse_args()

        module = ModuleRegister.get(args.module_name)
        m = module(args)

        m.run()

    def __init__(self,args):
        pass

    def onReceiveClient(self,request):
        pass

    def onReceiveServer(self,response):
        pass

    def onCommunication(self,request,response):
        pass
