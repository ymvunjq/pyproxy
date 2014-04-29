#!/usr/bin/env python
# -*- coding: utf-8 -*-

import select
import socket
from copy import copy
from threading import Thread
from network import TCPSocket,UDPSocket

from proxy import Proxy,logger

MAX_DATA_RECV=4096

class Layer4Proxy(Proxy):
    @classmethod
    def create_arg_subparser(cls,parser):
        parser.add_argument("--server-ip",default="127.0.0.1",metavar="IP",help="IP Server to connect to")
        parser.add_argument("--server-port",default=80,metavar="PORT",type=int,help="Port Server to connect to")

    def __init__(self,args):
        Proxy.__init__(self,args)
        self.server_ip = args.server_ip
        self.server_port = args.server_port
        self.dst = (self.server_ip,self.server_port)

    def getServerAddr(self,data):
        return (self.server_ip,self.server_port)

    def bind(self):
        s = self._socket_(client=True)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host,self.port))
        return s

    def init_forward(self,addr,client_sock=None):
        s = self._socket_(client=False)
        try:
            logger.debug("Connect to %r" % (addr,))
            s.connect(addr)
        except socket.error as e:
            logger.warning("Connect to %r : %s" % (addr,e))
        s.set_associate(client_sock)
        return s

class ForwarderTCP(Thread):
    """ Handle communication between client and server """
    def __init__(self,proxy,client_sock):
        Thread.__init__(self)
        # copy because we want to change instance object in a thread without modifying other threads
        self.proxy = copy(proxy)
        self.client_sock = client_sock

    def run(self):
        self.proxy.manage_connection(self.client_sock)

@Proxy.register
class TCPProxy(Layer4Proxy):
    _socket_ = TCPSocket

    def bind(self):
        s = Layer4Proxy.bind(self)
        s.listen(200)
        return s

    def manage_connection(self,client_sock):
        """ Manage one connection """
        server_sock = self.init_forward((self.server_ip,self.server_port),client_sock)
        self.forward((client_sock,server_sock))
        server_sock.close()
        client_sock.close()

    def accept(self):
        client_sock,client_addr = self.sock.accept()
        client_sock = TCPSocket(client=True,sock=client_sock)
        logger.debug("New client: %r" % (client_addr,))
        return client_sock

    def read_on_sockets(self,socks):
        real_socks = map(lambda s:s.sock,socks)
        while not self.stop:
            (read,write,error) = select.select(real_socks,[],real_socks,self.timeout)
            if error:
                continue
            elif read:
                for sock in read:
                    try:
                        data = sock.recv(MAX_DATA_RECV)
                    except socket.error:
                        yield (r,"")
                    r = filter(lambda s:s.sock == sock,socks)[0]
                    yield (r,data)

    def run(self):
        threads = []
        try:
            while True:
                logger.debug("Waiting for new client...")
                client_sock = self.accept()
                th = ForwarderTCP(self,client_sock)
                th.start()
                threads.append(th)
        except KeyboardInterrupt:
            pass

        self.sock.close()

        for th in threads:
            th.proxy.stop = True


@Proxy.register
class UDPProxy(Layer4Proxy):
    _socket_ = UDPSocket

    def __init__(self,args):
        Layer4Proxy.__init__(self,args)
        self.server_socks = {}

    def init_forward(self,addr,client_sock=None):
        s = Layer4Proxy.init_forward(self,addr,client_sock)
        s.addr = addr
        return s

    def read_on_sockets(self,socks):
        real_socks = list(set(map(lambda s:s.sock,socks)))
        (read,write,error) = select.select(real_socks,[],real_socks,self.timeout)
        if read:
            for sock in read:
                data,addr = sock.recvfrom(MAX_DATA_RECV)
                r = filter(lambda s:s.match(sock,addr),socks)
                if len(r) == 0:
                    s = UDPSocket(client=True,sock=sock,addr=addr)
                    socks.append(s)
                    yield (s,data)
                else:
                    yield (r[0],data)

    def run(self):
        try:
            self.forward([self.sock])
        except KeyboardInterrupt:
            pass

        self.sock.close()
