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
from winHeader import WindowHeader
import socket, json, logging, time

MAXBUF = 1024

logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s]  %(message)s'
        )

class ChatClient():
    def __init__(self):
        self.qToWinMan = Queue()
        self.qFromWinMan = Queue()
        self.winManager = WinManager(self.qFromWinMan, self.qToWinMan)
        self.name = None
        self.sock = None
        self.winManager.newWindow('Hall', 'Public')

        pass

    def _setName(self):
        self.name = self.winManager.popUpWindow('AskS', 'Name', 'What\'s your name?')
        if not self.name:
            exit(1)
        return None
    
    def setSockInfo(self, address, port, family=socket.AF_INET, protocol=socket.SOCK_STREAM):
        self.sockInfo = (family, protocol, address, port)
        return None

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
            header, msg = self.qFromWinMan.get()
            
            if header.command == 'H':       # Help Command
                pass                        # msg is None
            elif header.command == 'W':     # Who's online Command
                pass                        # msg is None
            elif header.command == 'SG':    # Show how many groups are online
                pass                        # msg is None
            elif header.command == 'GM':    # Show group members Command
                pass                        # msg is None
            elif header.command == 'B':     # Broadcast Command
                pass                        # msg is Message
            elif header.command == 'N':     # Get now who's onlien except self
                pass                        # msg is None
            elif header.command == 'NG':    # New Group Room Command
                pass                        # msg is group name
            elif header.command == 'NREQ':  # Send the request
                pass                        # msg is " id. name  "
            elif header.command == 'P':     # Prviate Message Command
                # Name is privateID
                logging.debug(f'{header.privateID}/{self.name}')
                data = json.dumps( (header.command, header.privateID, msg) )
                data = data.encode()
                self.sock.send(data)
                continue
            elif header.command == 'G':     # Group Message Command
                # Name is groupID
                logging.debug(f'{header.groupID}/{self.name}')
                data = json.dumps( (header.command, header.groupID, msg) )
                data = data.encode()
                self.sock.send(data)
                continue
            elif header.command == 'IG':    # Invite user to group Command
                logging.debug(f'{header.groupID}/{msg}')
                data = json.dumps( (header.command, header.groupID, msg) )
                data = data.encode()
                self.sock.send(data)
                continue
            elif header.command == 'PQ':
                # This means user leave pri room, should talk to server and close window
                self.winManager.closeWindowById(header.winID)
                msg = str(header.privateID)
                logging.debug(f'In Client After Q, cmd is {header.command}, msg is {msg}')                
            elif header.command == 'GQ':
                # This means user leave group room, should talk to server and close window
                self.winManager.closeWindowById(header.winID)
                msg = header.groupID
            
            # Transform data
            data = json.dumps( (header.command, self.name, msg) )
            data = data.encode()
            # Send data
            self.sock.send(data)
            
            if header.command == 'Q':
                # After tell the server user want to leave, close window
                self.winManager.closeWindowById(header.winID)
                self.sock.close()
                time.sleep(3)
                exit()
        
    def _getRepFromServer(self):
        """ 
        Run in another thread
        Server 指示該做甚麼
        """
        header = WindowHeader()
        while True:
            # Get reply from sever
            data = self.sock.recv(MAXBUF)
            if data:
                data = data.decode()
                # Data is (Command, Sender's name, Message)
                cmd, senderInfo, msg = json.loads(data)
                logging.debug(f'Client get reply from server cmd is {cmd}, senderInfo is {senderInfo}, msg is {msg}')
            else:
                # data = ''
                break
            if cmd == 'B':
                # SenderInfo is sender's name
                header.setHeader(None, None, 'Public', 'B')
                header.setOption(sender=senderInfo)
                self.qToWinMan.put( (header, msg) )
                #self.qToWinMan.put( ('Public', sender, msg) )
            elif cmd == 'P':
                # SenderInfo is PID/SenderName
                header.setHeader(None, None, 'Private', 'P')
                priID, senderName = int(senderInfo.split('/')[0]), senderInfo.split('/')[1]
                header.setOption(sender=senderName, pID=priID)
                self.qToWinMan.put( (header, msg) )
            elif cmd == 'PQ':
                header.setHeader(None, None, 'Private', 'PQ')
                priID, senderName = int(senderInfo.split('/')[0]), senderInfo.split('/')[1]
                header.setOption(sender=senderName, pID=priID)
                self.qToWinMan.put( (header, msg) )
                #self.qToWinMan.put( ('Private', sender, msg) )
            elif cmd == 'G':
                # SenderInfo is GID/SenderName
                header.setHeader(None, None, 'Group', 'G')
                groupID, senderName = int(senderInfo.split('/')[0]), senderInfo.split('/')[1]
                header.setOption(sender=senderName, gID=groupID)
                self.qToWinMan.put( (header,msg) )
            elif cmd == 'GQ':
                pass
            elif cmd == 'N':
                onlineList = msg.split('\n')
                #logging.debug('In Reply cmd is N, List is {}'.format(onlineList))
                self.winManager.popUpWindow('AskW', 'Select User', onlineList)
                pass
            elif cmd == 'NG':
                gID, groupName = msg
                winID = self.winManager.newWindow(groupName, 'Group', GID=gID)
                self.winManager.activeWindow(winID)
            elif cmd == 'NREQ':
                # Response is yes or no
                # SenderInfo is ID/Name
                response = self.winManager.popUpWindow('AskQ', 'Privat talk', msg)
                response = response + '/' + senderInfo  # Response is yes(no)/ID/Name
                data = json.dumps( ('NREQ', self.name, response) )
                self.sock.send(data.encode())
            elif cmd == 'NREP':
                if msg == 'Refuse':
                    # Pop refuse Info window
                    # SenderInfo is senderName
                    self.winManager.popUpWindow('Info', 'Private Talk',
                                                '{} refuses to talk with you'.format(senderInfo))
                else:
                    # Create new Privat Chat Window
                    # Privat Window name is sender name, SenderInfo is senderName
                    # msg will be PID
                    winID = self.winManager.newWindow(senderInfo, 'Private', msg)
                    self.winManager.activeWindow(winID)
            elif cmd == 'ERROR':
                self.winManager.popUpWindow('Info', 'Can\'t Open Room', msg)
            elif cmd == 'H':
                self.winManager.popUpWindow('Info', 'Help Message', msg)
            elif cmd == 'W':
                self.winManager.popUpWindow('Info', 'Who\'s Online', msg)
            elif cmd == 'SG':
                # SenderInfo is a flag, 1 -> has group info, 0 -> no group info
                if senderInfo:
                    groupInfo = ''
                    for group in msg:
                        groupInfo += '{}. {}\n    Members: {}'.format(group[0][0], group[0][1], group[1])
                        groupInfo += '\n'
                else:
                    groupInfo = msg
                self.winManager.popUpWindow('Info', 'Group online', groupInfo)     
            elif cmd == 'IG':
                gID = senderInfo
                self.winManager.popUpWindow('Invite', 'Invite User to Group', msg, GID=gID)
            elif cmd == 'IGQ':
                # Invite to Group Query
                gID, groupName = int(senderInfo.split('/')[0]), senderInfo.split('/')[1]
                # Get user response which is either yer or no
                response = self.winManager.popUpWindow('AskQ', 'Invited to Group', msg)
                if response == 'yes':
                    data = json.dumps( ('IGQ', gID, 'yes') )
                    self.sock.send(data.encode())
                    winID = self.winManager.newWindow(groupName, 'Group', GID=gID)
                    self.winManager.activeWindow(winID)
            elif cmd == 'GM':
                groupInfo = ''
                for user in msg:
                    groupInfo += '{}. {}'.format(user[0], user[1])
                self.winManager.popUpWindow('Members', 'Who in Group', groupInfo)
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
        
        self.winManager.activeWindow(1) # Hall's winID must 1
        logging.info('Close program...')
        
if __name__ == '__main__':
    Client = ChatClient()
    Client.setSockInfo('127.0.0.1', 10732)
    Client.Run()
    
    """
    parser = argparse.ArgumentParser(description='This is Chat Room Client')
    parser.add_argument('host', help='Input the host address')
    parser.add_argument('-p', metavar='Port', help='Choose the port which the server is listening at')
    
    args = parser.parse_args()
    Client = ChatClient()
    Client.setSockInfo(parser.host, parser.p)
    Client.Run()
    
    """