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

class HTTPComm(object):
    """ Request/Response HTTP """
    separator = "\r\n"

    def __init__(self,data):
        self.raw = data
        self.data = []
        if self.isCompleteHeaders():
            self.parse()

    def __str__(self):
        return self.raw

    def parse_headers(self,data):
        l = len(HTTPComm.separator)
        r = InsensitiveDict()
        headers = data.split(HTTPComm.separator)
        for line in headers:
            indice = line.find(": ")
            key,value = line[:indice],line[indice+2:]
            r[key] = value
        return r

    def parse(self):
        """ Parse HTTP Communication """
        l = len(HTTPComm.separator)

        try:
            # First line
            end_line = self.raw.find(HTTPComm.separator)
            self.parse_first_line(self.raw[:end_line])

            # Headers
            end_headers = self.raw.find(HTTPComm.separator+HTTPComm.separator,end_line+l)
            self.headers = self.parse_headers(self.raw[end_line+l:end_headers])

            # Data
            self.data = self.raw[end_headers+2*l:]
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.critical("Unable to parse %r" % self.raw)
            logger.critical("TRACEBACK: %s" % ("\n".join(traceback.format_exception(exc_type,exc_value,exc_traceback)),))
            raise RuntimeError, "Critical Error Parsing"

    def isCompleteHeaders(self):
        return not self.raw.find(HTTPComm.separator*2) == -1

    def isCompleteData(self):
        if "COntent-length" in self.headers:
            length = int(self.headers["Content-Length"])
            return len(self.data) == length
        elif "Transfer-Encoding" in self.headers:
            i = 0
            l = len(self.data)
            stop = False
            while not stop:
                j = self.data.find(HTTPComm.separator,i)
                if j == -1:
                    return False
                length = int(self.data[i:j],16)
                # Shall stop with chunk of size 0
                if length == 0:
                    stop = True
                i = j+2
                if i+length+2 > l:
                    return False
                i += length+2
        return True

    def isComplete(self):
        if not self.isCompleteHeaders():
            return False
        return self.isCompleteData()


    def append(self,data):
        if self.isCompleteHeaders():
            self.data = self.data + data
            self.raw = self.raw + data
        else:
            self.raw = self.raw + data
            if self.isCompleteHeaders():
                self.parse()

class Request(HTTPComm):
    """ Request sent by HTTP Client """
    @classmethod
    def split_first_line(cls,line):
        return line.split(" ")

    def parse_first_line(self,line):
        self.method,self.url,self.version = Request.split_first_line(line)

    def proxyfy(self):
        """ Change URL received (http://..) with only path and add host header """
        l = len(HTTPComm.separator)

        end_line = self.raw.find(HTTPComm.separator)
        method,url,version = Request.split_first_line(self.raw[:end_line])
        url = re.search("(?P<method>http?)://(?P<hostname>[^/]+)(?P<uri>.*)", url)

        if self.isCompleteHeaders():
            headers = self.headers
        else:
            end_headers = self.raw.find(HTTPComm.Separator*2)
            end_headers = end_headers if end_headers != -1 else len(self.raw)
            headers = self.parse_headers(self.raw[end_line+l:end_headers])

        host_field = "Host: %s%s" % (url.group("hostname"),HTTPComm.separator) if "Host" not in headers else ""

        s = "{method} {url} {version}{separator}{host_header}{remaining_data}".format(method=method,url=url.group("uri"),version=version,separator=HTTPComm.separator,host_header=host_field,remaining_data=self.raw[end_line+l:])
        return s

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
    def __init__(self,conn,client_addr,from_client,from_server,fcom,timeout=3):
        Thread.__init__(self)
        self.conn = conn
        self.client_addr = client_addr
        self.from_client = from_client
        self.from_server = from_server
        self.fcom = fcom
        self.timeout = timeout
        self.stop = False
        self.requests = [] # list of requests waiting for responses

    @staticmethod
    def urlparse(url):
        """ Return tuple (ip,port) """
        req = urlparse.urlparse(url)
        netloc = req.netloc if len(req.netloc) > 0 else req.path
        if ":" in netloc:
            x = netloc.split(":")
            return (x[0],int(x[1]))
        else:
            return (netloc,443 if req.scheme == "https" else 80)

    def forward_http(self,client):
        """ Proxyfy between client and server """
        response = None
        socks = [self.conn,client]
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
                        if s == self.conn:  # From web client
                            out = client

                            if len(self.requests) == 0 or self.requests[-1].isComplete():
                                req = Request(data)
                                self.from_client(req)
                                data = req.proxyfy()
                                self.requests.append(req)
                            else:
                                #print "> DATA: %r" % data
                                self.requests[-1].append(data)
                        else: # From web server
                            out = self.conn
                            if not response:
                                response = Response(data)
                                if response.isComplete():
                                    #print "< DATA: %r" % data
                                    self.from_server(response)
                                    assert len(self.requests) > 0
                                    request = self.requests.pop(0)
                                    assert request.isComplete()
                                    self.fcom(request,response)
                                    response = None
                            else:
                                response.append(data)
                        out.send(data)
                    else:
                        return

    def forward_https(self,client):
        """ Proxyfy between client and server """
        socks = [self.conn,client]
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
                        if s == self.conn:  # From web client
                            out = client
                        else: # From web server
                            out = self.conn
                        out.send(data)
                    else:
                        return

    def run(self):
        try:
            data = self.conn.recv(MAX_DATA_RECV)
        except socket.error as e:
            logger.warning("%s" % e)
            self.conn.close()
            return

        if len(data) != 0:
            request = Request(data)
            self.requests.append(request)
            self.from_client(request)

            # URL Parsing
            ip,port = ThreadProxy.urlparse(request.url)

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                logger.debug("Connect to (%s,%u)" % (ip,port))
                s.connect((ip,port))
            except socket.error as e:
                logger.warning("Connect to (%s,%u) : %s" % (ip,port,e))
            else:
                if request.method == "CONNECT":
                    self.conn.send("%s 200 Connection established\n\n" % request.version)
                    self.forward_https(s)
                else:
                    data = request.proxyfy()
                    s.send(data)
                    self.forward_http(s)
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
        threads = []
        try:
            while True:
                client_sock,client_addr = self.sock.accept()
                th = ThreadProxy(client_sock,client_addr,self.onReceiveClient,self.onReceiveServer,self.onCommunication)
                th.start()
                threads.append(th)
        except KeyboardInterrupt:
            pass

        self.sock.close()

        for t in threads:
            t.stop = True
