#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import socket,select
import urlparse
from threading import Thread
import logging

MAX_DATA_RECV=4096

logger = logging.getLogger("PYPROXY")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
store = logging.FileHandler("pyproxy.log")
store.setFormatter(formatter)
logger.addHandler(store)

class HTTPComm(object):
    """ Request/Response HTTP """
    def __init__(self,data):
        self.raw = data
        self.data = []
        self.headers = {}
        self.parse()

    def __str__(self):
        return self.raw

    def parse(self):
        sep = "\r\n"
        l = len(sep)
        end_first_line = self.raw.find(sep)
        self.parse_first_line(self.raw[:end_first_line])
        end_headers = self.raw.find(sep+sep,end_first_line+l)

        headers = self.raw[end_first_line+l:end_headers].split(sep)
        for line in headers:
            key,value = line.split(": ")
            self.headers[key] = value

        self.data = self.raw[end_headers+2*l:]

    def isComplete(self):
        if "Content-Length" in self.headers:
            length = int(self.headers["Content-Length"])
            return len(self.data) == length
        return True

    def append(self,data):
        self.data = self.data + data

class Request(HTTPComm):
    """ Request sent by HTTP Client """
    def parse_first_line(self,line):
        self.method,self.url,self.version = line.split(" ")

class Response(HTTPComm):
    """ Response sent by HTTP server """
    def parse_first_line(self,line):
        end_version = line.find(" ")
        self.version = line[:end_version]
        end_code = line.find(" ",end_version+1)
        self.code = int(line[end_version+1:end_code])
        self.code_response = line[end_code+1:]

class ThreadProxy(Thread):
    """ Handle HTTP Proxy communication between client and server """
    def __init__(self,conn,client_addr,from_client,from_server,fcom,timeout=60):
        self.conn = conn
        self.client_addr = client_addr
        self.from_client = from_client
        self.from_server = from_server
        self.fcom = fcom
        self.timeout = timeout
        self.request = None
        self.response = None

    def forward(self,client):
        socks = [self.conn,client]
        while True:
            (read,write,error) = select.select(socks,[],socks,self.timeout)
            if error:
                return
            if read:
                for s in read:
                    data = s.recv(MAX_DATA_RECV)
                    if len(data) > 0:
                        if s == self.conn:
                            out = client
                            if not self.request:
                                self.request = Request(data)
                                if self.request.isComplete():
                                    self.from_client(self.request)
                            else:
                                self.request.append(data)
                        else:
                            out = self.conn
                            if not self.response:
                                self.response = Response(data)
                                if self.response.isComplete():
                                    self.from_server(self.response)
                                    self.fcom(self.request,self.response)
                                    self.request = None
                                    self.response = None
                            else:
                                self.response.append(data)
                        out.send(data)
                    else:
                        return

    def run(self):
        data = self.conn.recv(MAX_DATA_RECV)

        if len(data) != 0:
            request = Request(data)
            self.request = request
            self.from_client(request)

            # URL Parsing
            req = urlparse.urlparse(request.url)
            if ":" in req.netloc:
                x = req.netloc.split(":")
                ip = x[0]
                port = int(x[1])
            else:
                ip = req.netloc
                port = 80

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip,port))
            s.send(data)
            self.forward(s)
            s.close()

        self.conn.close()

class Proxy(object):
    def __init__(self,port=8080,host="127.0.0.1",modules=[]):
        self.port = port
        self.host = host
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host,self.port))
        self.sock.listen(200)
        self.modules = modules

    def onReceiveClient(self,request):
        for m in self.modules:
            m.onReceiveClient(request)

    def onReceiveServer(self,response):
        for m in self.modules:
            m.onReceiveServer(response)

    def onCommunication(self,request,response):
        for m in self.modules:
            m.onCommunication(request,response)

    def run(self):
        while True:
            client_sock,client_addr = self.sock.accept()
            handle = ThreadProxy(client_sock,client_addr,self.onReceiveClient,self.onReceiveServer,self.onCommunication).run()

