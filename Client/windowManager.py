# -*- coding: utf-8 -*-
"""
Created on Sat Dec 21 13:54:12 2019

@author: 劉又聖
"""
"""
Window Manager 用來管理多個視窗的I/O
  跑兩個Thread：一個接收Input from Window；一個接受Output from Client
  利用 Window Name 判斷訊息要送去哪
    此 Window Name 等同於 Client 端的 Sender Name
  Window Information Contains：
    (WindowID, WindowName, WindowType, WindowInstance)
    1. WinID：由 WinManager 管理
    2. WinName：大廳為 'Hall'，其餘用 接收者名稱命名
    3. WinType：只有兩種 'Public' or 'Private'
    4. WinInstance： Window 物件
  資料傳送規定：
    A1. From Window：(Message)
          1. In fun local have WinType and WinName
    A2. To Client：(Command, WinType, Message)
          1. Command 可以判度行為
          2. WinType 可以判斷是群聊還是私聊
          3. Message 沒有特殊格式
    B1. From Client：(WinType, Sender,Message)
          1. WinType 可以判斷是群聊還是私聊
          2. Sender 可以判斷要送給哪個視窗
          3. Message 沒有特殊格式
    B2. To Window：(Message)
        1. Message 格式化輸出
"""
from window import ChatWindow
from window import PriChatWindow
from queue import Queue
from threading import Thread
import logging

logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)s]  %(message)s'
        )

class WinManager():
    def __init__(self, queueToClient, queueFromClient):
        self.qFromClient = queueFromClient
        self.qToClient = queueToClient
        self.winList = []   # Each WinInfo is (WinID, WinName, WinType, WinInstance)
        self.winID = 1
        
        self.Run()
        
    def _isCmd(self, data):
        if data[0] == '/':
            return True 
        else:
            return False
    
    def _getCmd(self, data):
        data = data[1:]     # Delete the started '/'
        if data[0] == 'H':
            # Help command
            return ('H', 'None')
        elif data[0:4] == 'NREQ':
            return ('NREQ', data[5:])
        elif data[0] == 'N':
            # New window for private talk
            return ('N', 'None')
        elif data[0] == 'Q':
            # Quit chat room
            return ('Q', 'None')
        elif data[0] == 'W':
            # Who's online command
            return ('W', 'None')
        else:
            # Command Not Found
            return ('CNF', 'None')
    
    def _getWindowByName(self, winName):
        for winInfo in self.winList:
            if winName == winInfo[1]:
                return winInfo[3]
        return None
    
    def _delWindowByWID(self, winID):
        idx = 0
        for winInfo in self.winList:
            if winInfo[0] == winID:
                self.winList.pop(idx)
                break
            idx += 1
    
    def _degShowWinList(self):
        for winInfo in self.winList:
            print('WID: {}, WName: {}, WType: {}, WObj: {}'.format(
                    winInfo[0], winInfo[1], winInfo[2], winInfo[3]
                    ))
     
    def _getFromWindow(self, winID, winName, winType, window):
        """ Run another thread, In newWindow function """
        while True:
            # Get user input from window
            data = window.getWindowMsg()
            if self._isCmd(data):
                # The command has argument could be None or Someone's name(private talke)
                cmd, msg = self._getCmd(data)
            else:
                # No command, the data is pure message
                if winType == 'Public':
                    cmd = 'B' 
                else:
                    cmd = 'P'
                msg = data
            # Send user input to client process
            self.qToClient.put( (cmd, winName, msg) )
            # Sub Window's thread need to leave
            if winType != 'Public' and cmd == 'Q':
                self._delWindowByWID(winID)
                break
    
    def _getFromClient(self):
        """ Run another thread, In Run function """
        while True:
            # Get data from client process 
            winType, sender, msg = self.qFromClient.get()
            msg = f'[{sender:>10s}]:\n    {msg}\n'
            
            if winType == 'Public':
                win = self._getWindowByName('Hall')
            else:
                win = self._getWindowByName(sender)
            #win.putWindowMsg(msg)
            if win != None:
                win.outputQueue.put(msg)

    def activeWindow(self, WName):
        for winInfo in self.winList:
            if winInfo[1] == WName:
                winInfo[3].runWindow()

    def closeWindow(self, WName):
        for winInfo in self.winList:
            if winInfo[1] == WName:
                winInfo[3].closeWindow()

    def newWindow(self, WName, WType):
        """
        Window Name is Hall or Someone's name
        Window Type is either Public or Private
        """
        if WType == 'Public':
            winObj = ChatWindow(WName, Queue(), Queue())
        else:
            winObj = PriChatWindow(self._getWindowByName('Hall').mainWindow,
                                   WName, Queue(), Queue())
        
        winInfo = (self.winID, WName, WType, winObj)
        self.winList.append(winInfo)
        self.winID += 1
                
        tW = Thread(name='WinManFromWindow', target=self._getFromWindow, args=winInfo)
        tW.daemon = True
        tW.start()
        
        logging.info('After new window show now window list information ...')
        self._degShowWinList()
    
    def popUpWindow(self, which, title, msg):
        win = self._getWindowByName('Hall')
        return win.popUpWindow(which, title, msg)
    
    def Run(self):
        t = Thread(name='WinManFromClient', target=self._getFromClient)
        t.daemon = True
        t.start()