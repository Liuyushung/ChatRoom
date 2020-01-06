# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 08:13:38 2020

@author: 劉又聖
"""

class WindowHeader():
    def __init__(self):
        self.winID = None
        self.winName = None
        self.winType = None
        self.command = None
    def setHeader(self, wID, wName, wType, cmd):
        self.winID = wID
        self.winName = wName
        self.winType = wType
        self.command = cmd
    def setOption(self, sender=None, pID=None, gID=None):
        self.sender = sender
        self.privateID = pID
        self.groupID = gID
    def getHeader(self):
        return (self.winID, self.winName, self.winType, self.command)
    
        