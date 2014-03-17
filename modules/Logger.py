#!/usr/bin/env python
# -*- coding: utf-8 -*-

from proxy import Proxy
from module import Module

@Module.register
class Logger(Module):
    _desc_ = "Logging Proxy"

    @classmethod
    def create_arg_subparser(cls,parser):
        parser.add_argument("--log-request",action="store_true",help="Print requests done by client")
        parser.add_argument("--log-response",action="store_true",help="Print responses sent by server")
        parser.add_argument("--log",action="store_true",help="Print request and responses")
        parser.add_argument("--headers",action="store_true",help="Print headers")
        parser.add_argument("--data",action="store_true",help="Print data")

    def __init__(self,args):
        Module.__init__(self,args)
        self.log_request = args.log_request
        self.log_response = args.log_response
        self.log = args.log
        self.data = args.data
        self.headers = args.headers

    def _print_headers(self,http,direction=">"):
        print "\n".join(["%s %s: %s" % (direction,k,v) for k,v in http.headers.iteritems()])

    def _print_data(self,http,direction=">"):
        print "%s %r" % (direction,http.data)

    def onReceiveClient(self,request):
        if self.log_request:
            print "> %s %s" % (request.method,request.url)
            if self.headers:
                self._print_headers(request)
            if self.data:
                self._print_data(request)
            print ""

    def onReceiveServer(self,response):
        if self.log_response:
            print "< %r %s" % (response.code,response.code_response)
            if self.headers:
                self._print_headers(request,"<")
            if self.data:
                self._print_data(request,"<")
            print ""

    def onCommunication(self,request,response):
        if self.log:
            print "%s %s => %r %s" % (request.method,request.url,response.code,response.code_response)
            print ""
