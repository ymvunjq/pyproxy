#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import select

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

    def getServerAddr(self,data):
        return (self.server_ip,self.server_port)

    def bind(self):
        s = socket.socket(socket.AF_INET, self.socket_protocol)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host,self.port))
        return s

    def init_forward(self,addr,client_sock):
        s = socket.socket(socket.AF_INET, self.socket_protocol)
        try:
            logger.debug("Connect to %r" % (addr,))
            s.connect(addr)
        except socket.error as e:
            logger.warning("Connect to %r : %s" % (addr,e))
        return s

@Proxy.register
class TCPProxy(Layer4Proxy):
    socket_protocol = socket.SOCK_STREAM

    def bind(self):
        s = Layer4Proxy.bind(self)
        s.listen(200)
        return s

    def manage_connection(self,client_sock):
        """ Manage one connection """
        server_sock = self.init_forward((self.server_ip,self.server_port),client_sock)
        self.forward(client_sock,server_sock)
        server_sock.close()
        client_sock.close()

    def accept(self):
        client_sock,client_addr = self.sock.accept()
        logger.debug("New client: %r" % (client_addr,))
        return client_sock


@Proxy.register
class UDPProxy(Layer4Proxy):
    socket_protocol = socket.SOCK_DGRAM

    def __init__(self,args):
        Layer4Proxy.__init__(self,args)
        self.server_socks = {}

    def forward(self):
        """ Proxyfy between client and server """
        socks = [self.sock]
        while True:
            (read,write,error) = select.select(socks,[],socks,self.timeout)
            if error:
                return
            if read:
                for s in read:
                    try:
                        data,addr = s.recvfrom(MAX_DATA_RECV)
                    except socket.error as e:
                        logger.warning("%s" % e)
                        return

                    if len(data) > 0:
                        if s == self.sock:  # From client
                            if not addr in self.server_socks:
                                server_sock = self.init_forward(self.sock)
                                self.server_socks[addr] = server_sock
                                socks.append(server_sock)
                            else:
                                server_sock = self.server_socks[addr]
                            self.onReceiveClient(data)
                            out = server_sock
                            dst = (self.server_ip,self.server_port)
                        else:
                            for addr,server_sock in self.server_socks.iteritems():
                                if server_sock == s:
                                    dst = addr
                                    break
                            else:
                                assert False, "Socket server not found"
                            self.onReceiveServer(data)
                            out = self.sock
                        out.sendto(data,dst)
                    else:
                        print "Should close UDP socket"

    def run(self):
        try:
            self.forward()
        except KeyboardInterrupt:
            pass

        self.sock.close()
