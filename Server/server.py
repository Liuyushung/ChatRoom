# -*- coding: utf-8 -*-
"""
Created on Fri Dec 20 15:51:39 2019

@author: 劉又聖
"""
from person import Person
import json, socket, logging
import threading, queue

MAXBUF = 1024
logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)s]  %(message)s'
        )

class ChatServer():
    def __init__(self):
        self.onlineList = []
        self.broadcastList = []
        self.privateList = []
        self.sendQueue = queue.Queue()
        
    def setSockInfo(self, address, port, family=socket.AF_INET, protocol=socket.SOCK_STREAM):
        self.sockInfo = (family, protocol, address, port)
    
    """ Function are related to ADD and DELETE  """
    def _addPerson(self, user):
        logging.debug(f'User {user.name} is online...')
        self.onlineList.append(user)
        self.broadcastList.append(user)
    
    def _addPairToPriList(self, person1, person2):
        self.privateList.append( (person1, person2) )
        logging.info('{Show Private List}')
        self._degShowPList()

    def _userOffline(self, user):
        print(user, 'is offline...')
        # First close socket
        user.sock.close()
        # Second delete from Online list
        for i in range(len(self.onlineList)):
            if user.id == self.onlineList[i].id:
                self.onlineList.pop(i)
                break
        # Third delete from Broadcast list
        for i in range(len(self.broadcastList)):
            if user.id == self.broadcastList[i].id:
                self.broadcastList.pop(i)
                break
        # Fourth delete from Private list
        pass
    
    def _deleteFromPriList(self, pname1, pname2):
        """ 考慮一個人同時和多人聊天 """
        i = 0
        for pair in self.privateList:
            if (pair[0].name == pname1 and pair[1].name == pname2) or \
            (pair[0].name == pname2 and pair[1].name == pname1):
                self.privateList.pop(i)
                break
            i += 1    
        pass
    
    """ Function are related to Boolean """
    def _isInPriList(self, pairName):
        tmp1 = ( self._getPersonByName(pairName[0]), self._getPersonByName(pairName[1]) )
        tmp2 = ( self._getPersonByName(pairName[1]), self._getPersonByName(pairName[0]) )
        if tmp1 in self.privateList or tmp2 in self.privateList:
            return True
        return False
    
    """ Function are related to GET """
    def _getPersonByID(self, ID):
        for user in self.onlineList:
            if user.id == ID:
                return user
        return None

    def _getPersonByName(self, Name):
        for user in self.onlineList:
            if user.name == Name:
                return user
        return None

    """ Function are related to Debug """
    def _degShowBList(self):
        print('Now there are these users online...')
        if not len(self.broadcastList):
            print('Nobody is Online...')
        else:
            for user in self.broadcastList:
                print(f'{user.id:>2}. {user.name:<10}')
        
    def _degShowPList(self):
        print('Now who in private tlak list...')
        if not len(self.privateList):
            print('Nobody in Private List...')
        else:
            for pair in self.privateList:
                print(f'{pair[0].name} and {pair[1].name}')

    """ Function are related to Send """
    def _sendPrivateTo(self, sender, receiver, msg):
        if self._isInPriList((sender, receiver)):
            data = json.dumps( ('P', sender, msg) )
            data = data.encode()
            self._getPersonByName(receiver).sock.send(data)
        
    def _sendNewPriReq(self, senderName, receiverObj, cmd):
        data = json.dumps( (cmd, senderName, f'{senderName} want to talk with you.') )
        bdata= data.encode()
        receiverObj.sock.send(bdata)

    def _sendHelpMsg(self, user):
        msg = """
        Help Prompt
        /H -> Get help prompt.
        /W -> Get Who's online list.
        /Q -> Leave this chat room.
        /N -> New a chat room with somebody else
        """
        data = json.dumps( ('H', 'Server', msg) )
        user.sock.send(data.encode())
            
    def _sendWhoOnline(self, sender, cmd='W'):
        msg = ''
        for user in self.onlineList:
            msg += f'{user.id:>2d}. {user.name:<10s}\n'
        data = json.dumps( (cmd, 'Server', msg) )
        sender.sock.send(data.encode())
    
    def _sendWhoOnlineV2(self, sender, cmd='N'):
        msg = ''
        for user in self.onlineList:
            if user.name == sender.name:
                continue
            msg += f'{user.id:>2d}. {user.name:<10s}\n'
        data = json.dumps( (cmd, 'Server', msg) )
        sender.sock.send(data.encode())

    def _broadcast(self):
        while True:
            sender, msg = self.sendQueue.get()
            data = json.dumps( ('B', sender, msg) )
            bdata = data.encode()
            
            for user in self.broadcastList:
                if user.name != sender:
                    user.sock.send(bdata)
    
    """ Function are related to Receive """
    def _asyncRecv(self, user):
        # user is person instance
        # user is sender
        while True:
            # data is (Command, Sender's name, Message)
            data = user.sock.recv(MAXBUF)
            cmd, sender, msg = json.loads(data.decode())
            logging.debug(f'In Async Recv cmd is {cmd}; sender is {sender}; msg is {msg}')
            
            if cmd == 'B':
                """ Boradcast message """
                self.sendQueue.put( (sender, msg) )
            elif cmd == 'H':
                """ Help command """
                self._sendHelpMsg(user)
            elif cmd == 'N':
                """ Send newest online user message to client """
                #self._sendWhoOnline(user, cmd)
                self._sendWhoOnlineV2(user, cmd)
            elif cmd == 'NREQ':
                if msg[0] == 'y':    
                    # This belong to another user's response
                    receiver = msg.split(' ')[1]    # [0] is yes, [1] is peer name
                    logging.debug('{} and {} will go private list'.format(sender, receiver))
                    # 新增到 Privat talk List
                    self._addPairToPriList(self._getPersonByName(receiver), user)
                    # Send NREP command to both
                    data = json.dumps( ('NREP', receiver, receiver) )
                    self._getPersonByName(sender).sock.send(data.encode())
                    data = json.dumps( ('NREP', sender, sender) )
                    self._getPersonByName(receiver).sock.send(data.encode())
                elif msg[0] == 'n':
                    # This belong to another user's response
                    receiver = msg.split(' ')[1]    # [0] is no, [1] is peer name
                    logging.debug('{} refuse {}\'s new talk invitaion.'.format(sender, receiver))
                    data = json.dumps( ('NREP', sender, 'Refuse') )
                    self._getPersonByName(receiver).sock.send(data.encode())
                else:
                    # This belong to user's request
                    # Send the new private talk request to another user
                    pID = int(msg.split('. ')[0])
                    logging.debug('pID is {}'.format(pID))
                    self._sendNewPriReq(sender, self._getPersonByID(pID), 'NREQ')
                pass
            elif cmd == 'P':
                """ Private talk command """
                sender, peer = sender.split(' ')
                self._sendPrivateTo(sender, peer, msg)
            elif cmd == 'Q':
                """ User need to leave """
                self._userOffline(user)
                self._degShowBList()
                break
            elif cmd == 'PQ':
                """ User leave Private talk """
                # msg is peer's name
                self._deleteFromPriList(user.name, msg)
                self._degShowPList()
                # Send PQ to peer
                pass
            elif cmd == 'W':
                """ Who is online command """
                self._sendWhoOnline(user, cmd)
            else:
                self._sendCmdNotFound(user)
              
    """ Public Function """
    def Run(self):
        listenSock = socket.socket(*self.sockInfo[:2])
        listenSock.bind(self.sockInfo[2:])
        listenSock.listen(5)
        print('Server active...\nListen at {}:{}...'.format(*self.sockInfo[2:]))
        
        tB = threading.Thread(name='ServerBroadcast', target=self._broadcast)
        tB.daemon = True
        tB.start()
        
        ID_num = 1  # Give to each connected person, it's an unique number
        while True:
            print('Waiting for connection...')
            conn_sock, peer = listenSock.accept()
            # Create person info
            name = conn_sock.recv(MAXBUF).decode()
            user = Person(ID_num, name, conn_sock)
            self._addPerson(user)
            # Registrar sucessed
            user.sock.send( json.dumps( (user.id, user.name) ).encode() )
            # Run Async Recv thread
            tR = threading.Thread(name=f"{name}'s Recv", target=self._asyncRecv, args=(user,))
            tR.daemon = True
            tR.start()
            # Increment ID number
            ID_num += 1
""" End Chat Server """

if __name__ == '__main__':
    Server = ChatServer()
    Server.setSockInfo('127.0.0.1', 10732)
    Server.Run()