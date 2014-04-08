#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket

from proxy import Proxy

class Layer4Proxy(Proxy):
    @classmethod
    def create_arg_subparser(cls,parser):
        parser.add_argument("--server-ip",default="127.0.0.1",metavar="IP",help="IP Server to connect to")
        parser.add_argument("--server-port",default=80,metavar="PORT",type=int,help="Port Server to connect to")

    def __init__(self,args):
        Proxy.__init__(self,args)
        self.server_ip = args.server_ip
        self.server_port = args.server_port

    def getServerAddr(self,data):
        return (self.server_ip,self.server_port)

    def bind(self):
        s = socket.socket(socket.AF_INET, self.socket_protocol)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host,self.port))
        s.listen(200)
        return s

    def connect(self,addr):
        return socket.socket(socket.AF_INET, self.socket_protocol)

@Proxy.register
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


@Proxy.register
class UDPProxy(Layer4Proxy):
    socket_protocol = socket.SOCK_DGRAM
