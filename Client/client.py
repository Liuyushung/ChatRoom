# -*- coding: utf-8 -*-
"""
Created on Fri Dec 20 15:51:41 2019

@author: 劉又聖
"""
"""
Client 端程式負責透過網路連線交換訊息
  執行三個Thread
    一個為接收User Input from Window Manager
    一個為接收Reply Output from Server
    一個為執行MainLoop
  資料傳送規定：
    A1.  From Window Manager：(Command, Window Name, Message)
    A2.  To Server Request：(Command, User Name, Message)
    
    B1.  From Server Reply：(Command, Sender Name, Message)
    B2.  To Window Manager：(Window Type, Sender Name, Message)
  所有命令種類：
    可由使用者輸入：
      1.  H -> Help
      2.  W -> Who's online
      3.  N -> New window with other user
      4.  Q -> Quit the chat room
    程式產生命令：
      1.  B -> Broadcast in Hall
            由 Window Manager 判斷Window Type後產生
      2.  P -> Private talk with another user
            由 Window Manager 判斷Window Type後產生
      3.  NREQ -> 新增Private Talk Window請求，需要等待 NREQ 指令回覆
            由 Client 端判斷 N command 後發出
            若由 Client 端接收            
      4.  NREP -> 回應NREQ請求
            由 Server 端取得回應後發出
      5.  PQ -> 關閉Privat Talk Window
      6.  CNF -> Command Not Found
"""

from windowManager import WinManager
from threading import Thread
from queue import Queue
import socket, json, logging, time

MAXBUF = 1024

logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)s]  %(message)s'
        )

class ChatClient():
    def __init__(self):
        self.qToWinMan = Queue()
        self.qFromWinMan = Queue()
        self.winManager = WinManager(self.qFromWinMan, self.qToWinMan)
        self.name = None
        self.sock = None
        self.sockInfo = (socket.AF_INET, socket.SOCK_STREAM, '127.0.0.1', 10732)    
        self.winManager.newWindow('Hall', 'Public')

        pass

    def _setName(self):
        self.name = self.winManager.popUpWindow('AskS', 'Get Name', 'What\'s your name?')
        if not self.name:
            exit(1)

    def _setUpConnection(self):
        self.sock = socket.socket(*self.sockInfo[:2])
        self.sock.connect(self.sockInfo[2:])

    def _register(self):
        self.sock.send(self.name.encode())
        msg = self.sock.recv(MAXBUF)
        # msg is (ID, Name)
        ID, name = json.loads(msg.decode())
        logging.info('Server reply: ID is {}, Name is {} ...'.format(ID, name))       

    def _getFromWinMan(self):
        """ Run in another thread """
        while True:
            # Get data from Window Manager
            cmd, winName, msg = self.qFromWinMan.get()
            logging.debug(f'Deal cmd is {cmd}, msg is {msg}')
            # These command don't need to handle H, W, B, P, N
            if cmd == 'CNF':
                self.winManager.popUpWindow('Info', 'Command Not Found!!', 'Try to type /H to get help.')
                continue
            elif cmd == 'P':
                data = json.dumps( (cmd, f'{self.name} {winName}', msg) )
                data = data.encode()
                self.sock.send(data)
                continue
            elif cmd == 'Q' and winName != 'Hall':
                cmd = 'PQ'
                self.winManager.closeWindow(winName)
                msg = winName
            
            # Transform data
            data = json.dumps( (cmd, self.name, msg) )
            data = data.encode()
            # Send data
            self.sock.send(data)
            
            if cmd == 'Q':
                logging.debug(f'Client handle cmd "{cmd}"')
                self.winManager.closeWindow(winName)
                self.sock.close()
                time.sleep(3)
                exit()
        
    def _getRepFromServer(self):
        """ 
        Run in another thread
        Server 指示該做甚麼
        """
        while True:
            # Get reply from sever
            data = self.sock.recv(MAXBUF)
            if data:
                data = data.decode()
                # Data is (Command, Sender's name, Message)
                cmd, sender, msg = json.loads(data)
                logging.debug(f'Client get reply from server cmd is {cmd}, sender is {sender}, msg is {msg}')
            else:
                # data = ''
                break
            if cmd == 'B':
                self.qToWinMan.put( ('Public', sender, msg) )
            elif cmd == 'P':
                self.qToWinMan.put( ('Private', sender, msg) )
            elif cmd == 'N':
                onlineList = msg.split('\n')
                logging.debug('In Reply cmd is N, List is {}'.format(onlineList))
                self.winManager.popUpWindow('AskW', 'Select User', onlineList)
                pass
            elif cmd == 'NREQ':
                response = self.winManager.popUpWindow('AskQ', 'Privat talk', msg)
                logging.debug('Response is {}'.format(response))
                response = response + ' ' + sender
                data = json.dumps( ('NREQ', self.name, response) )
                self.sock.send(data.encode())
            elif cmd == 'NREP':
                if msg == 'Refuse':
                    # Pop refuse Info window
                    self.winManager.popUpWindow('Info', 'Private Talk',
                                                '{} refuses to talk with you'.format(sender))
                else:
                    # Create new Privat Chat Window
                    # Privat Window name is sender name
                    self.winManager.newWindow(sender, 'Private')
                    self.winManager.activeWindow(sender)
            elif cmd == 'H':
                self.winManager.popUpWindow('Info', 'Help Message', msg)
            elif cmd == 'W':
                self.winManager.popUpWindow('Info', 'Who\'s Online', msg)
            else:
                self.winManager.popUpWindow('Info', 'Command Not Found!!', 'Try to type /H to get help.')
            
    def Run(self):
        self._setName()
        self._setUpConnection()
        self._register()
        
        tW = Thread(name='ClientGetFromWinManager', target=self._getFromWinMan)
        tW.daemon = True
        tW.start()
        
        tS = Thread(name='ClientGetRepFromServer', target=self._getRepFromServer)
        tS.daemon = True
        tS.start()
        
        self.winManager.activeWindow('Hall')
        logging.info('Close program...')
        
if __name__ == '__main__':
    Client = ChatClient()
    Client.Run()