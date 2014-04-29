#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from module import Module,PassThrough

def hexdump(direction,s,size=16):
    """ Hexdump data """
    def out(c):
        if ord(c) < 32 or ord(c) > 126: sys.stdout.write(".")
        else: sys.stdout.write(c)

    s = list(s)
    sys.stdout.write("%s " % direction)
    for i in xrange(len(s)):
        sys.stdout.write("%02x " % ord(s[i]))
        if i != 0 and i%size == size-1:
            sys.stdout.write("\t\t|")
            for j in xrange(i-size+1,i+1):
                out(s[j])
            sys.stdout.write("|\n%s " % direction)
    l = len(s)
    m = l%size
    sys.stdout.write("%s\t\t|" % (" "*(size-m)*3,))
    for i in xrange(l-m,l):
        out(s[i])
    sys.stdout.write("%s|\n" % (" "*(size-m),))

def output(direction,s):
    print "%s %s" % (direction,s)

@Module.register("TCPProxy","UDPProxy","HTTPProxy")
class Logger(PassThrough):
    _desc_ = "Layer 4 Logging Proxy"

    @classmethod
    def create_arg_subparser(cls,parser):
        parser.add_argument("--log-request",action="store_true",help="Print requests done by client")
        parser.add_argument("--log-response",action="store_true",help="Print responses sent by server")
        parser.add_argument("-H","--hex",action="store_true",help="Print data in hexa")


    def __init__(self,args):
        Module.__init__(self,args)
        self.log_request = args.log_request
        self.log_response = args.log_response
        if args.hex:
            self.output = hexdump
        else:
            self.output = output

    def onReceiveClient(self,request):
        if self.log_request:
            self.output(">",request)
        return request

    def onReceiveServer(self,response):
        if self.log_response:
            self.output("<",response)
        return response
