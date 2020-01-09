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
from window import GroupChatWindow
from queue import Queue
from threading import Thread
from winHeader import WindowHeader
import logging

logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s]  %(message)s'
        )

class WinManager():
    def __init__(self, queueToClient, queueFromClient):
        self.qFromClient = queueFromClient
        self.qToClient = queueToClient
        self.winList = []   # Each WinInfo is (WinID, WinName, WinType, WinInstance)
        self.winID = 1
        
        self.Run()
    
    def _getWindowByName(self, winName):
        for winInfo in self.winList:
            if winName == winInfo[1]:
                return winInfo[3]
        return None
    
    def _getWindowByPID(self, PID):
        for winInfo in self.winList:
            if isinstance(winInfo[3], PriChatWindow) and PID == winInfo[3].priID:
                return winInfo[3]
        logging.error('Get Win PID not found {}'.format(PID))
        return None
    
    def _getWindowByGID(self, GID):
        for winInfo in self.winList:
            if isinstance(winInfo[3], GroupChatWindow) and GID == winInfo[3].groupID:
                return winInfo[3]
        logging.error('Get Win PID not found {}'.format(GID))
        return None
    
    def _delWindowByWID(self, winID):
        idx = 0
        for winInfo in self.winList:
            if winInfo[0] == winID:
                self.winList.pop(idx)
                logging.debug('Pop the Window WName: {}, WType: {}'.format(
                    winInfo[1], winInfo[2]))
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
            header, msg = window.getWindowMsg()
            # Send user input to client process
            self.qToClient.put( (header, msg) )
            
    def _getFromClient(self):
        """ Run another thread, In Run function """
        while True:
            # Get data from client process 
            header, msg = self.qFromClient.get()
            msg = f'[{header.sender:>10s}]:\n    {msg}\n'
            # Get the correct room
            if header.winType == 'Public':
                win = self._getWindowByName('Hall')
            elif header.winType == 'Private':
                win = self._getWindowByPID(header.privateID)
            else:
                # Group
                win = self._getWindowByGID(header.groupID)
            if win:
                win.outputQueue.put(msg)

    def activeWindow(self, winID):
        for winInfo in self.winList:
            if winInfo[0] == winID:
                winInfo[3].runWindow()
                break
    
    def closeWindowById(self, winID):
        i = 0
        for winInfo in self.winList:
            if winInfo[0] == winID:
                winInfo[3].closeWindow()
                self.winList.pop(i)
                break
            i+=1

    def newWindow(self, WName, WType, PID=None, GID=None):
        """
        Window Name is Hall or Someone's name
        Window Type is either Public or Private
        """
        if WType == 'Public':
            winObj = ChatWindow(self.winID, WName, WType, Queue(), Queue())
        elif WType == 'Private':
            winObj = PriChatWindow(self._getWindowByName('Hall').mainWindow,
                                   PID, self.winID, WName, WType, Queue(), Queue())
        else:
            # Wtype == 'Group'
            winObj = GroupChatWindow(self._getWindowByName('Hall').mainWindow,
                                     GID, self.winID, WName, WType, Queue(), Queue())
        
        winInfo = (self.winID, WName, WType, winObj)
        self.winList.append(winInfo)
        self.winID += 1
                
        tW = Thread(name='WinManFromWindow', target=self._getFromWindow, args=winInfo)
        tW.daemon = True
        tW.start()
        
        return self.winID - 1
        
    def popUpWindow(self, which, title, msg, GID=None):
        if GID:
            win = self._getWindowByGID(GID)
        else:
            win = self._getWindowByName('Hall')
        return win.popUpWindow(which, title, msg)
    
    def Run(self):
        t = Thread(name='WinManFromClient', target=self._getFromClient)
        t.daemon = True
        t.start()