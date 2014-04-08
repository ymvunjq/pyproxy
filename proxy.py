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
    def __init__(self,sock_client,proxy,ip,port,timeout=3):
        Thread.__init__(self)
        self.sock_client = sock_client
        self.proxy = proxy
        self.timeout = timeout
        self.server_ip = ip
        self.server_port = port
        self.stop = False

    def forward(self,sock_server):
        """ Proxyfy between client and server """
        socks = [self.sock_client,sock_server]
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
                        if s == self.sock_client:  # From client
                            out = sock_server
                            self.proxy.onReceiveClient(data)
                        else: # From server
                            out = self.sock_client
                            self.proxy.onReceiveServer(data)
                        out.send(data)
                    else:
                        return

    def run(self):
        try:
            data = self.sock_client.recv(MAX_DATA_RECV)
        except socket.error as e:
            logger.warning("%s" % e)
            self.sock_client.close()
            return

        if len(data) != 0:
            self.proxy.onReceiveClient(data)

            s = self.proxy.connect()
            self.forward(s)
            s.close()

        self.conn.close()

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
        self.port = args.port
        self.host = args.bind
        m = module.ModuleRegister.get(args.module_name)
        self.modules = [m(args)]
        self.sock = self.bind()

    def connect(self):
        pass

    def close(self,sock):
        sock.close()

    def onReceiveClient(self,request):
        for m in self.modules:
            m.onReceiveClient(request)

    def onReceiveServer(self,response):
        for m in self.modules:
            m.onReceiveServer(response)

    def run(self):
        threads = []
        try:
            while True:
                client_sock,client_addr = self.sock.accept()
                th = ThreadProxy(client_sock,self.onReceiveClient,self.onReceiveServer)
                th.start()
                threads.append(th)
        except KeyboardInterrupt:
            pass

        self.sock.close()

        for t in threads:
            t.stop = True
