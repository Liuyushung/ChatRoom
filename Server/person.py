# -*- coding: utf-8 -*-
"""
Created on Fri Dec 20 16:09:03 2019

@author: 劉又聖
"""

class Person():
    def __init__(self, ID, name, conn_sock=None):
        self.id = ID
        self.name = name
        self.sock = conn_sock
        
    def __str__(self):
        if self.sock:
            return 'ID: {}. Name: {}'.format(self.id, self.name)
        else:
            return 'Person is not initialized'

def formatToWindow(data):
    pass