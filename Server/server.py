# -*- coding: utf-8 -*-
"""
Created on Fri Dec 20 15:51:39 2019

@author: 劉又聖
"""
from person import Person
import json, socket, logging
import threading, queue, argparse

MAXBUF = 1024
logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s]  %(message)s'
        )

class ChatServer():
    def __init__(self):
        self.onlineList = []
        self.broadcastList = []     # Elems are person instance
        self.privateList = []       # Elems are (PID, person1, person2)
        self.groupList = []         # Elems are ((GID, GroupName), preson1, person2, ...)
        self.sendQueue = queue.Queue()
        self.UID = 1
        self.PID = 1
        self.GID = 1
        
    def setSockInfo(self, address, port, family=socket.AF_INET, protocol=socket.SOCK_STREAM):
        self.sockInfo = (family, protocol, address, port)
        return None
    
    """ Function are related to ADD and DELETE  """
    def _addPerson(self, user):
        logging.debug(f'User {user.name} is online...')
        self.onlineList.append(user)
        self.broadcastList.append(user)
        return None
    
    def _addPairToPriList(self, PID, person1, person2):
        """ person1 and person2 are Person Instance """
        self.privateList.append( (PID, person1, person2) )
        logging.info('{Show Private List}')
        self._degShowPList()
        return None

    def _addPersonToGroup(self, GID, user):
        groupRoom = self._getGroupRoomByGID(GID)
        groupRoom.append(user)
        self._sendGroupTo(GID, user, 'Welcome {} join the group!'.format(user.name))
        return None        
    
    def _newGroup(self, user, groupName):
        # Group should be dynamic adjust
        self.groupList.append( [ (self.GID, groupName), user ] )
        self.GID += 1
        return (self.GID-1, groupName)
       
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
        return None
    
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
        return None
    
    def _deletePersonFromGroupList(self, GID, UID):
        room = self._getGroupRoomByGID(GID)
        
        for idx in range(1, len(room)):
            if room[idx].id == UID:
                room.pop(idx)
                if len(room) == 1:
                    # No members in group, should be popped
                    self._deleteGroupFromGroupList(GID)
                break
        return None

    def _deleteGroupFromGroupList(self, GID):
        idx = 0
        for room in self.groupList:
            if room[0][0] == GID:
                self.groupList.pop(idx)
                break
            idx += 1
        return None
    
    """ Function are related to GET """
    def _getPersonByID(self, UID):
        for user in self.onlineList:
            if user.id == UID:
                return user
        #logging.error('Get Person UID {} is None'.format(UID))
        return None
    
    def _getPriRoomByPID(self, PID):
        for room in self.privateList:
            if room[0] == PID:
                return room
        #logging.error('Get Private PID {} is None'.format(PID))
        return None
    
    def _getGroupRoomByGID(self, GID):
        for room in self.groupList:
            if room[0][0] == GID:
                return room
        #logging.error('Get Group GID {} is None'.format(GID))
        return None
    
    """ Function are related to Debug """
    def _degShowBList(self):
        print('{*** Now show the users are online ***}')
        if not len(self.broadcastList):
            print('Nobody is Online...')
        else:
            for user in self.broadcastList:
                print(f'{user.id:>2}. {user.name:<10}')
        return None
        
    def _degShowPList(self):
        print('{*** Now show the private tlak list ***}')
        if not len(self.privateList):
            print('  Nobody in Private List...')
        else:
            for pair in self.privateList:
                print(f'  PID: {pair[0]}, {pair[1].name} and {pair[2].name}')
        return None
    
    def _degShowGList(self):
        print('{*** Now show the group list ***}')
        if not len(self.groupList):
            print('   Nobody in Group List...', end='')
        else:
            for room in self.groupList:
                print('   {}. {}: '.format(room[0][0], room[0][1]), end='')
                for idx in range(1, len(room)):
                    print('{} '.format(room[idx].name), end='')
        print()
        return None

    """ Function are related to Send """
    def _sendPrivateTo(self, PID, sender, msg, cmd):
        # cmd is P or PQ. P is user send; PQ is server send
        room = self._getPriRoomByPID(PID)
        
        if cmd == 'P':
            senderName = sender.name
        else:
            senderName = 'Server'
            
        if room:
            data = json.dumps( (cmd, str(PID)+'/'+senderName, msg) )
            data = data.encode()
            # Find the peer to send
            if room[1].id != sender.id:
                room[1].sock.send(data)
            else:
                room[2].sock.send(data)
        return None
                
    def _sendGroupTo(self, GID, sender, msg, cmd=None):
        # cmd is G or GQ. G is user send; GQ is server send
        room = self._getGroupRoomByGID(GID)
        
        if cmd == 'G':
            senderName = sender.name
        else:
            senderName = 'Server'
            
        if room:
            data = json.dumps( (cmd, str(GID)+'/'+senderName, msg) )
            data = data.encode()
            
            for idx in range(1, len(room)):     # room[0] is always (GID, groupName)
                if room[idx].id != sender.id:
                    room[idx].sock.send(data)
        return None

    def _sendNewPriReq(self, sender, receiver, cmd='NREQ'):
        idAndName = str(sender.id) + '/' + sender.name
        data = json.dumps( (cmd, idAndName, f'{sender.name} want to talk with you.') )
        bdata= data.encode()
        receiver.sock.send(bdata)
        return None
    
    def _sendInviteGroup(self, sender, GID, invitedList, cmd='IGQ'):
        groupName = self._getGroupRoomByGID(GID)[0][1]
        msg = '{} invite you to his group {}'.format(
                sender.name, groupName)
        data = json.dumps( (cmd, str(GID)+'/'+groupName, msg) )
        data = data.encode()
        for uID in invitedList:
            self._getPersonByID(uID).sock.send(data)
        return None
    
    def _sendHelpMsg(self, user):
        msg = """
        Help Prompt
        You can talk to everyone in the hall.
        You can choose one user to chat in another private room.
        But you can't leave the hall.
        """
        data = json.dumps( ('H', 'Server', msg) )
        user.sock.send(data.encode())
        return None
            
    def _sendWhoOnline(self, sender, cmd='W'):
        msg = ''
        for user in self.onlineList:
            msg += f'{user.id:>2d}. {user.name:<10s}\n'
        data = json.dumps( (cmd, 'Server', msg) )
        sender.sock.send(data.encode())
        return None
    
    def _sendWhoOnlineV2(self, sender, cmd='N'):
        msg = ''
        for user in self.onlineList:
            if user.id == sender.id:
                continue
            msg += f'{user.id:>2d}. {user.name:<10s}\n'
        data = json.dumps( (cmd, 'Server', msg) )
        sender.sock.send(data.encode())
        return None
    
    def _sendWhoOnlineV3(self, sender, GID, cmd='IG'):
        msg = []
        for user in self.onlineList:
            if user.id == sender.id:
                continue
            msg.append( (user.id, user.name) )
        data = json.dumps( (cmd, GID, msg ) )
        sender.sock.send(data.encode())
        return None
    
    def _sendWhoInGroup(self, sender, GID, cmd='GM'):
        msg = []
        groupRoom = self._getGroupRoomByGID(GID)
        if groupRoom:
            for idx in range(1, len(groupRoom)):
                msg.append( (groupRoom[idx].id, groupRoom[idx].name) )
            data = json.dumps( (cmd, None, msg) )
            sender.sock.send(data.encode())
        return None
    
    def _sendGroupInfos(self, sender, cmd='SG'):
        msg = []
        hasGroupFlag = None
        if len(self.groupList) != 0:
            hasGroupFlag = 1
            for group in self.groupList:
                personList = ''
                for idx in range(1, len(group)):
                    personList += group[idx].name + ' '
                msg.append( (group[0], personList) )
        else:
            hasGroupFlag = 0
            msg = 'There are no group online...'
        print(msg)
        data = json.dumps( (cmd, hasGroupFlag, msg ) )
        sender.sock.send(data.encode())
        return None

    def _broadcast(self):
        while True:
            uID, sender, msg = self.sendQueue.get()
            data = json.dumps( ('B', sender, msg) )
            bdata = data.encode()
            
            for user in self.broadcastList:
                if user.id != uID:
                    user.sock.send(bdata)
        return None

    def _serverBroadcast(self, msg, uID=None):
        data = json.dumps( ('B', 'Server', msg) )
        bdata = data.encode()
        
        for user in self.broadcastList:
            if user.id != uID:
                user.sock.send(bdata)
        return None
    
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
                self.sendQueue.put( (user.id, user.name, msg) )
            elif cmd == 'H':
                """ Help command """
                self._sendHelpMsg(user)
            elif cmd == 'N':
                """ Send newest online user message to client """
                self._sendWhoOnlineV2(user, cmd)
            elif cmd == 'NG':
                # Create a new group record
                groupInfos = self._newGroup(user, msg)      # groupInfos are (GID, groupName)
                # Send the group information to user
                data = json.dumps( (cmd, 'Server', groupInfos) )
                user.sock.send(data.encode())
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
                        data = json.dumps( ('ERROR', user.name, 'You have been token with {}'.format(peer.name)))
                        user.sock.send(data.encode())
                    else:
                        # It is not opened
                        self._sendNewPriReq(user, peer, 'NREQ')
                pass
            elif cmd == 'P':
                """ Private talk command """
                priID = int(sender)
                self._sendPrivateTo(priID, user, msg, cmd)
            elif cmd == 'G':
                """ Group talk command  """
                groupID = int(sender)
                self._sendGroupTo(groupID, user, msg, cmd)
            elif cmd == 'Q':
                """ User need to leave """
                self._userOffline(user)
                break
            elif cmd == 'PQ':
                """ User leave Private talk """
                # msg is PID
                pID = int(msg)
                msg = '{} has left the chat room...'.format(user.name)
                # Send PQ to peer
                self._sendPrivateTo( pID, user, msg, cmd)
                # Delete this person from Private List
                self._deleteFromPriList(PID=pID)
            elif cmd == 'GQ':
                """ User leave Group talk """
                # msg is GID
                gID = int(msg)
                msg = '{} has the the chat room...'.format(user.name)
                # Send GQ to group member
                self._sendGroupTo(gID, user, msg, cmd)                
                # Delete this person from Group List
                self._deletePersonFromGroupList(gID, user.id)
            elif cmd == 'W':
                """ Who is online command """
                self._sendWhoOnline(user, cmd)
            elif cmd == 'SG':
                """ Show how many groups are online """
                self._sendGroupInfos(user)
            elif cmd == 'GM':
                """ Show who in the group """
                gID = sender
                self._sendWhoInGroup(user, gID, cmd='GM')
            elif cmd == 'IG':
                gID = sender
                if msg == 'query':
                    # Query how many user are online
                    self._sendWhoOnlineV3(user, gID, cmd)
                else:
                    logging.debug('IG msg is {}'.format(msg))
                    # Send the Invite Group Query to user in the invited list
                    # msg is [UID, UID....]
                    self._sendInviteGroup(user, gID, msg, cmd='IGQ')
            elif cmd == 'IGQ':
                gID = sender
                if msg == 'yes':
                    self._addPersonToGroup(gID, user)
            else:
                self._sendCmdNotFound(user)
    
    def _SuperUser(self):
        while True:
            command = input()
            if command == 'showB':
                self._degShowBList()
            elif command == 'showP':
                self._degShowPList()
            elif command == 'showG':
                self._degShowGList()
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
    
    """
    parser = argparse.ArgumentParser(description='This is Chat Room Server')
    parser.add_argument('host', help='Input the host address')
    parser.add_argument('-p', metavar='Port', help='Choose the port which the server will listen at')
    
    args = parser.parse_args()
    Server = ChatServer()
    Server.setSockInfo(parser.host, parser.p)
    Server.Run()
    """