#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import socket,select
import traceback
from threading import Thread
import logging
import re

import module
from modules import *

MAX_DATA_RECV=4096

logger = logging.getLogger("PYPROXY")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
store = logging.FileHandler("pyproxy.log")
store.setFormatter(formatter)
logger.addHandler(store)


class ThreadProxy(Thread):
    """ Handle communication between client and server """
    def __init__(self,proxy,client_sock):
        Thread.__init__(self)
        self.proxy = proxy
        self.client_sock = client_sock

    def run(self):
        self.proxy.manage_connection(self.client_sock)

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

    def onReceiveClient(self,request):
        """ Hook to add action on packet reception from client """
        for m in self.modules:
            m.onReceiveClient(request)

    def onReceiveServer(self,response):
        """ Hook to add action on packet reception from server """
        for m in self.modules:
            m.onReceiveServer(response)

    def init_forward(self):
        pass

    def manage_connection(self,client_sock):
        pass

    def forward(self,client_sock,server_sock):
        """ Proxyfy between client and server """
        socks = [client_sock,server_sock]
        while not self.stop:
            (read,write,error) = select.select(socks,[],socks,self.timeout)
            if error:
                return
            if read:
                for s in read:
                    try:
                        data = s.recv(MAX_DATA_RECV)
                    except socket.error as e:
                        logger.warning("%s" % e)
                        return

                    if len(data) > 0:
                        if s == client_sock:  # From client
                            out = server_sock
                            self.onReceiveClient(data)
                        else: # From server
                            out = client_sock
                            self.onReceiveServer(data)
                        out.send(data)
                    else:
                        return

    def run(self):
        threads = []
        try:
            while True:
                logger.debug("Waiting for new client...")
                client_sock = self.accept()
                th = ThreadProxy(self,client_sock)
                th.start()
                threads.append(th)
        except KeyboardInterrupt:
            pass

        self.sock.close()

        self.stop = True
