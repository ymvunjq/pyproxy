#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging

import module
from modules import *

MAX_DATA_RECV=4096

logger = logging.getLogger("PYPROXY")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
store = logging.FileHandler("pyproxy.log")
store.setFormatter(formatter)
logger.addHandler(store)


class ProxyRegister(object):
    registry = {}

    @classmethod
    def register(cls,obj,key="__name__"):
        cls.registry[getattr(obj,key)] = obj
        return obj

    @classmethod
    def get(cls, name, default=None):
        return cls.registry.get(name, default)

    @classmethod
    def itervalues(cls):
        return cls.registry.itervalues()


class Proxy(object):
    _desc_ = "N/A"

    @staticmethod
    def register(f):
        return ProxyRegister.register(f,key="__name__")

    @classmethod
    def create_arg_parser(cls,parser):
        subparser = parser.add_subparsers(dest="proxy_name",help="Proxy")
        for proxy in ProxyRegister.itervalues():
            p = subparser.add_parser(proxy.__name__,help=proxy._desc_)

            # Add available modules for this proxy
            p = module.Module.create_arg_parser(p,proxy.__name__)

            proxy.create_arg_subparser(p)

        return parser

    @classmethod
    def create_arg_subparser(cls,parser):
        pass

    def __init__(self,args):
        self.timeout = 3
        self.port = args.port
        self.host = args.bind
        m = module.ModuleRegister.get(args.module_name)
        self.modules = [m(args)]
        self.sock = self.bind()
        self.stop = False

    def close(self,sock):
        sock.close()

    def onReceiveClient(self,data):
        """ Hook to add action on packet reception from client """
        for m in self.modules:
            data = m.onReceiveClient(data)
        return data

    def onReceiveServer(self,data):
        """ Hook to add action on packet reception from server """
        for m in self.modules:
            data = m.onReceiveServer(data)
        return data

    def manage_connection(self,client_sock):
        pass

    def forward(self,socks):
        while not self.stop:
            for sin,data in self.read_on_sockets(socks):
                if sin.is_client():
                    hook = self.onReceiveClient
                else:
                    hook = self.onReceiveServer
                if not sin.has_associate():
                    sout = self.init_forward(self.dst)
                    sout.set_associate(sin)
                    socks.append(sout)
                else:
                    sout = sin.get_associate()
                if len(data) == 0:
                    self.stop = True
                    return
                data = hook(data)
                sout.send(data)
