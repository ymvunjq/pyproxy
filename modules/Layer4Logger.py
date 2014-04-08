#!/usr/bin/env python
# -*- coding: utf-8 -*-

from module import Module

@Module.register
class Layer4Logger(Module):
    _desc_ = "Layer 4 Logging Proxy"

    @classmethod
    def create_arg_subparser(cls,parser):
        parser.add_argument("--log-request",action="store_true",help="Print requests done by client")
        parser.add_argument("--log-response",action="store_true",help="Print responses sent by server")

    def __init__(self,args):
        Module.__init__(self,args)
        self.log_request = args.log_request
        self.log_response = args.log_response

    def onReceiveClient(self,request):
        if self.log_request:
            print "> %s" % (request,)

    def onReceiveServer(self,response):
        if self.log_response:
            print "< %s" % (response,)
