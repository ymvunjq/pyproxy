#!/usr/bin/env python
# -*- coding: utf-8 -*-

class InsensitiveDict(dict):
    def __setitem__(self, key, value):
        super(InsensitiveDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(InsensitiveDict, self).__getitem__(key.lower())

    def __contains__(self,key):
        return super(InsensitiveDict, self).__contains__(key.lower())
