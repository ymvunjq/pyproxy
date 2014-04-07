#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import socket,select
import urlparse
import traceback
from threading import Thread
import logging
import re

from utils import InsensitiveDict

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

class Proxy(object):
    def __init__(self,server_ip,server_port,port=8080,host="127.0.0.1",modules=[]):
        self.server_ip = server_ip
        self.server_port = server_port
        self.port = port
        self.host = host
        self.modules = modules
        self.sock = self.bind()

    def getServerAddr(self,data):
        return (self.server_ip,self.server_port)

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

class Layer4Proxy(Proxy):
    def bind(self):
        s = socket.socket(socket.AF_INET, self.socket_protocol)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host,self.port))
        s.listen(200)
        return s

    def connect(self,addr):
        return socket.socket(socket.AF_INET, self.socket_protocol)

class TCPProxy(Layer4Proxy):
    socket_protocol = socket.SOCK_STREAM

    def connect(self,addr):
        s = self.connect(addr)
        try:
            logger.debug("Connect to (%s,%u)" % (addr[0],addr[1]))
            s.connect(addr)
        except socket.error as e:
            logger.warning("Connect to (%s,%u) : %s" % (addr[0],addr[1],e))
        return s


class UDPProxy(Layer4Proxy):
    socket_protocol = socket.SOCK_DGRAM
