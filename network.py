#!/usr/bin/env/python
# -*- coding: utf-8 -*-

import socket

class Socket(object):
    def __init__(self,client,protocol,domain=socket.AF_INET,sock=None):
        if sock is None:
            self.sock = socket.socket(domain,protocol)
        else:
            self.sock = sock
        self.client = client
        self.associate = None

    def __getattr__(self,attr):
        return getattr(self.sock,attr)

    def is_client(self):
        return self.client

    def is_server(self):
        return not self.client

    def has_associate(self):
        return not self.associate is None

    def get_associate(self):
        return self.associate

    def set_associate(self,s):
        self.associate = s
        s.associate = self

class TCPSocket(Socket):
    def __init__(self,client,*args,**kargs):
        Socket.__init__(self,client,protocol=socket.SOCK_STREAM,*args,**kargs)

class UDPSocket(Socket):
    def __init__(self,client,addr=None,*args,**kargs):
        Socket.__init__(self,client,protocol=socket.SOCK_DGRAM,*args,**kargs)
        self.addr = addr

    def match(self,sock,addr):
        if self.is_client():
            return self.sock == sock and self.addr == addr
        else:
            return self.sock == sock and self.getpeername() == addr

    def __repr__(self):
        return "<UDPSocket sock:%r addr:%r client:%r>" % (self.sock,self.addr,self.client)

    def send(self,data):
        self.sendto(data,self.addr)

class Endpoint(object):
    pass

class Link(object):
    pass
