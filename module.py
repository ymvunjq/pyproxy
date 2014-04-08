#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict

class ModuleRegister(object):
    registry = defaultdict(dict)

    @classmethod
    def register(cls,obj,proxys,key="__name__"):
        for proxy in proxys:
            cls.registry[proxy][getattr(obj,key)] = obj
        return obj

    @classmethod
    def get(cls,name,default=None):
        for k,v in cls.registry.iteritems():
            if name in v:
                return cls.registry[k][name]
        return default

    @classmethod
    def itervalues(cls,proxy):
        return cls.registry[proxy].itervalues()

class Module(object):
    _desc_ = "N/A"

    @staticmethod
    def register(*args):
        def wrapper(f):
            return ModuleRegister.register(f,args,key="__name__")
        return wrapper

    @classmethod
    def create_arg_parser(cls,parser,proxy):
        subparsers = parser.add_subparsers(dest="module_name",help="Modules")
        for module in ModuleRegister.itervalues(proxy):
            p = subparsers.add_parser(module.__name__,help=module._desc_)
            module.create_arg_subparser(p)

        return parser

    @classmethod
    def create_arg_subparser(cls,parser):
        pass

    def __init__(self,args):
        pass

    def onReceiveClient(self,request):
        pass

    def onReceiveServer(self,response):
        pass

    def onCommunication(self,request,response):
        pass
