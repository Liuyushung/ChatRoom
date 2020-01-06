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
        self.UID = 1
        self.PID = 1
        
    def setSockInfo(self, address, port, family=socket.AF_INET, protocol=socket.SOCK_STREAM):
        self.sockInfo = (family, protocol, address, port)
    
    """ Function are related to ADD and DELETE  """
    def _addPerson(self, user):
        logging.debug(f'User {user.name} is online...')
        self.onlineList.append(user)
        self.broadcastList.append(user)
    
    def _addPairToPriList(self, PID, person1, person2):
        """ person1 and person2 are Person Instance """
        self.privateList.append( (PID, person1, person2) )
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
        self._deleteFromPriList(UID=user.id)
        # Send offline message to Hall
        self._serverBroadcast('{} has left the chat room!'.format(user.name), user.id)
    
    def _deleteFromPriList(self, PID=None, UID=None):
        """
        Two Case:
        One is called cause Private Talk.
        One is called cause User offline.
        """
        if PID:
            # This is called by Private Talk.
            i = 0
            for room in self.privateList:
                if room[0] == PID:
                    self.privateList.pop(i)
                    break
                i += 1
        if UID:
            # This is called by User offline.
            i, popList = 0, []
            for room in self.privateList:
                if room[1].id == UID:
                    popList.insert(0, i)
                elif room[2].id == UID:
                    popList.insert(0, i)
                i += 1
            for popIdx in popList:
                self.privateList.pop(popIdx)
    
    """ Function are related to GET """
    def _getPersonByID(self, UID):
        for user in self.onlineList:
            if user.id == UID:
                return user
        return None

    def _getPersonByName(self, Name):
        for user in self.onlineList:
            if user.name == Name:
                return user
        return None
    
    def _getPriRoomByPID(self, PID):
        for room in self.privateList:
            if room[0] == PID:
                return room
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
            print('  Nobody in Private List...')
        else:
            for pair in self.privateList:
                print(f'  PID: {pair[0]}, {pair[1].name} and {pair[2].name}')

    """ Function are related to Send """
    def _sendPrivateTo(self, PID, senderName, msg, cmd):
        # cmd is P or PQ. P is user send; PQ is server send
        room = self._getPriRoomByPID(PID)
        if room:
            data = json.dumps( (cmd, str(PID)+'/'+senderName, msg) )
            data = data.encode()
            # Find the peer to send
            if room[1].name != senderName:
                room[1].sock.send(data)
            else:
                room[2].sock.send(data)

    def _sendNewPriReq(self, sender, receiver, cmd='NREQ'):
        idAndName = str(sender.id) + '/' + sender.name
        data = json.dumps( (cmd, idAndName, f'{sender.name} want to talk with you.') )
        bdata= data.encode()
        receiver.sock.send(bdata)

    def _sendHelpMsg(self, user):
        msg = """
        Help Prompt
        You can talk to everyone in the hall.
        You can choose one user to chat in another private room.
        But you can't leave the hall.
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
            if user.id == sender.id:
                continue
            msg += f'{user.id:>2d}. {user.name:<10s}\n'
        data = json.dumps( (cmd, 'Server', msg) )
        sender.sock.send(data.encode())

    def _broadcast(self):
        while True:
            uID, sender, msg = self.sendQueue.get()
            data = json.dumps( ('B', sender, msg) )
            bdata = data.encode()
            
            for user in self.broadcastList:
                if user.id != uID:
                    user.sock.send(bdata)

    def _serverBroadcast(self, msg, uID=None):
        data = json.dumps( ('B', 'Server', msg) )
        bdata = data.encode()
        
        for user in self.broadcastList:
            if user.id != uID:
                user.sock.send(bdata)
                
    """ Check function """
    def _checkPriIsExist(self, sender, peer):
        for pair in self.privateList:
            if (pair[1].id == sender.id and pair[2].id == peer.id) or \
                (pair[2].id == sender.id and pair[1].id == peer.id):
                    return True
        return False
            
    """ Function are related to Receive """
    def _asyncRecv(self, user):
        # !! user is person instance
        # user is sender
        while True:
            # data is (Command, Sender's name, Message)
            data = user.sock.recv(MAXBUF)
            cmd, sender, msg = json.loads(data.decode())    # sender == user.name
            logging.debug(f'In Async Recv cmd is {cmd}; sender is {sender}; msg is {msg}')
            
            if cmd == 'B':
                """ Boradcast message """
                self.sendQueue.put( (user.id, sender, msg) )
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
                    receiverID = int(msg.split('/')[1])    # [0] is yes, [1] is peer ID, [2] is peer Name
                    # Get the receiver instance
                    receiver = self._getPersonByID(receiverID)
                    # 新增到 Privat talk List
                    self._addPairToPriList(self.PID, receiver, user)
                    # Send NREP command to both
                    data = json.dumps( ('NREP', receiver.name, self.PID) )
                    user.sock.send(data.encode())
                    data = json.dumps( ('NREP', user.name, self.PID) )
                    receiver.sock.send(data.encode())
                    # Increment the Private room ID
                    self.PID += 1
                elif msg[0] == 'n':
                    # This belong to another user's response
                    receiverID = int(msg.split('/')[1])    # [0] is no, [1] is peer ID, [2] is peer Name
                    # Get the receiver instance
                    receiver = self._getPersonByID(receiverID)
                    logging.debug('{} refuse {}\'s new talk invitaion.'.format(user.name, receiver.name))
                    data = json.dumps( ('NREP', user.name, 'Refuse') )
                    receiver.sock.send(data.encode())
                else:
                    # This belong to user's request
                    # Send the new private talk request to another user
                    uID = int(msg.split('. ')[0])
                    logging.debug('peer\'s uID is {}'.format(uID))
                    peer = self._getPersonByID(uID)
                    # Before sending the request, check if the room has been open
                    if self._checkPriIsExist(user, peer):
                        # It has been opened
                        data = json.dumps( ('ERROR', sender, 'You have been token with {}'.format(peer.name)))
                        user.sock.send(data.encode())
                    else:
                        # It is not opened
                        self._sendNewPriReq(user, peer, 'NREQ')
                pass
            elif cmd == 'P':
                """ Private talk command """
                infos = sender.split('/')   # sender contains PID, senderName
                priID, sender = int(infos[0]), infos[1]
                self._sendPrivateTo(priID, sender, msg, cmd)
            elif cmd == 'Q':
                """ User need to leave """
                self._userOffline(user)
                self._degShowBList()
                break
            elif cmd == 'PQ':
                """ User leave Private talk """
                # msg is PID
                pID = int(msg)
                msg = '{} has left the chat room...'.format(sender)
                # Send PQ to peer
                self._sendPrivateTo( pID, sender, msg, cmd)
                # msg is peer's name
                self._deleteFromPriList(PID=pID)
                self._degShowPList()
                
            elif cmd == 'W':
                """ Who is online command """
                self._sendWhoOnline(user, cmd)
            else:
                self._sendCmdNotFound(user)
    
    def _SuperUser(self):
        while True:
            command = input()
            if command == 'showB':
                self._degShowBList()
            elif command == 'showP':
                self._degShowPList()
            else:
                print('Command Not Found...')
    
    """ Public Function """
    def Run(self):
        listenSock = socket.socket(*self.sockInfo[:2])
        listenSock.bind(self.sockInfo[2:])
        listenSock.listen(5)
        print('Server active...\nListen at {}:{}...'.format(*self.sockInfo[2:]))
        
        tB = threading.Thread(name='ServerBroadcast', target=self._broadcast)
        tB.daemon = True
        tB.start()
        
        tS = threading.Thread(name='SuperUser', target=self._SuperUser)
        tS.daemon = True
        tS.start()
        
        while True:
            #print('Waiting for connection...')
            conn_sock, peer = listenSock.accept()
            # Create person info
            name = conn_sock.recv(MAXBUF).decode()
            user = Person(self.UID, name, conn_sock)
            self._addPerson(user)
            # Registrar sucessed
            user.sock.send( json.dumps( (user.id, user.name) ).encode() )
            # Run Async Recv thread
            tR = threading.Thread(name=f"{name}'s Recv", target=self._asyncRecv, args=(user,))
            tR.daemon = True
            tR.start()
            # Server boradcast message
            self._serverBroadcast('Welcome {} join the chat room!'.format(name))
            # Increment ID number
            self.UID += 1
            
""" End Chat Server """

if __name__ == '__main__':
    Server = ChatServer()
    Server.setSockInfo('127.0.0.1', 10732)
    Server.Run()