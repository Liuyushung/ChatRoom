# -*- coding: utf-8 -*-
"""
Created on Wed Dec 18 19:49:40 2019

@author: 劉又聖
"""

import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk
from queue import Queue
from threading import Thread
from winHeader import WindowHeader
import logging

logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)s]  %(message)s'
        )

class ChatWindow():
    """ 
    My Demo Window
    Contains three frame
    One Label
    One Text
    One Entry and one button
    """
    def __init__(self, winID, winName, winType,inQueue=Queue(), outQueue=Queue(), BgColor=None):
        #self.priID, self.groupID = None, None
        self.winID = winID
        self.winName = winName
        self.winType = winType
        self.inputQueue = inQueue       # This window input field
        self.outputQueue = outQueue     # This window output field
        self.QuitFlag = False           # There are many to close window could need to prevent send /Q duplicate
        # Window Font and color
        self.FontSetting = ('Console', 16)
        if not BgColor: 
            self.BgColor = '#BBFF66'
        else:
            self.BgColor = BgColor
        # Window Widget
        self.frameList = []
        self.mainWindow = None
        self.menubar = None
        self.filemenu = None
        self.onlineLabel = None
        self.outputText = None
        self.inputEntry = None
        self.sendButton = None
        # Set up Widget
        self._setMainWindow()
        self._setWidget()
        self._setMenubar()
        self._setWidgetPosition()
        self._setEvent()
        # Run window
        #self.runWindow()
    
    """ Start Set Function """
    def _setMainWindow(self):
        self.mainWindow = tk.Tk()
        self.mainWindow.geometry('500x450+500+200')
        self.mainWindow.title(self.winName)
        self.mainWindow['bg'] = self.BgColor        
    
    def _setWidget(self):        
        for i in range(3):
            self.frameList.append(tk.Frame(self.mainWindow, bg=self.BgColor))
        
        self.onlineLabel = tk.Label(self.frameList[0], text="Welcome to public chat room",
                                    font=('Comic Sans MS', 18, 'bold'),
                                    bg=self.BgColor)
        
        self.outputText = tk.Text(self.frameList[1], font=self.FontSetting, height=17, width=48,
                                  state=tk.DISABLED, relief='solid')
        self.outputText.tag_config('self', foreground='blue', justify=tk.RIGHT)
        self.outputText.tag_config('server', foreground='red')
        
        self.inputEntry = tk.Entry(self.frameList[2], font=self.FontSetting, width=38)
        
        self.sendButton = tk.Button(self.frameList[2], text="Send", font=self.FontSetting,
                                    bg='#99BBFF', relief='ridge', borderwidth=3,
                                    command=self._getInput)
    
    def _setMenubar(self):
        def funExit():
            self.QuitFlag = True
            self._sendMessage('Q')
            
        self.menubar = tk.Menu(self.mainWindow)
        
        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label='Get help', command=lambda:self._sendMessage('H'))
        self.helpmenu.add_command(label='Who\'s Online', command=lambda:self._sendMessage('W'))
        self.helpmenu.add_command(label='Talk with...', command=lambda:self._sendMessage('N'))
        self.helpmenu.add_separator()
        self.helpmenu.add_command(label='Exit', command=funExit)
        
        self.menubar.add_cascade(label='Help', menu=self.helpmenu)
        self.mainWindow.config(menu=self.menubar)
    
    def _setWidgetPosition(self):
        for frame in self.frameList:
            frame.pack()
        self.onlineLabel.pack()
        self.outputText.pack()
        self.inputEntry.grid(row=1, column=0, columnspan=8)
        self.sendButton.grid(row=1, column=10, columnspan=2, padx=20)

    def _enterEvent(self, event):
        # User can press Enter to send Message
        self._getInput()
        
    def _setEvent(self):
        self.mainWindow.bind('<Return>', self._enterEvent)
        self.mainWindow.protocol('WM_DELETE_WINDOW', self.closeWindow)
    
    """ End Set Function """
    def _sendMessage(self, cmd, msg=None, PID=None):
        header = WindowHeader()
        header.setHeader(self.winID, self.winName, self.winType, cmd)
        if PID:
            header.setOption(pID=PID)
        
        self.inputQueue.put((header, msg))
        
    def _asyncInsertOutput(self):
        serverType = '[    Server]'
        while True:
            msg = self.outputQueue.get()
            if msg[:12] == serverType:
                self.outputText['state'] = tk.NORMAL
                self.outputText.insert('end', msg, 'server')
                self.outputText['state'] = tk.DISABLED
            else:
                self.outputText['state'] = tk.NORMAL
                self.outputText.insert('end', msg)
                self.outputText['state'] = tk.DISABLED
            
    def _getInput(self):
        msg = self.inputEntry.get()
        if msg:
            self._insertSelfMsg(msg)
            self.inputEntry.delete(0, tk.END)
            
            if self.winType == 'Public':
                self._sendMessage('B', msg)
            elif self.winType == 'Private':
                self._sendMessage('P', msg, PID=self.priID)
            else:
                self._sendMessage('G', msg)
        
    def _insertSelfMsg(self, msg):
        msg += '\n'
        self.outputText['state'] = tk.NORMAL
        self.outputText.insert(tk.END, msg, 'self')
        self.outputText['state'] = tk.DISABLED
    
    def _selectUserPopWindow(self, title, userList):
        def sendResultToWinMan():
            # Format of result is " id. UserName    ", Server will use this pattern
            result = getSelected.get()
            logging.debug('In select pop window get the result is {}'.format(result))
            self._sendMessage('NREQ', msg=result) 
            peerName = result.split('. ')[1].split(' ')[0]
            self.popUpWindow('Info', 'Server Reply', f'Wait for {peerName}\'s answer ...')
            popWin.destroy()
        # Format user List
        for i in range(len(userList)):
            if not userList[i]:
                userList.pop(i)
                break
        # Create one topLevel, title <-> label, userList <-> ComboBox, button <-> Yes or No
        popWin = tk.Toplevel(self.mainWindow)
        popWin.title('New Private Talk Window')
        popWin.geometry=('350x300')
        popWin.wm_attributes('-topmost', 1)
        # Set up Label for title
        titleLabel = tk.Label(popWin, font=self.FontSetting,
                              text='Select online user\nwhom you want to talk with.',
                              justify=tk.CENTER, pady=5)
        titleLabel.pack()
        # Set up ComboBox for select which user
        getSelected = tk.StringVar()
        comboBox = ttk.Combobox(popWin, width=15, textvariable=getSelected,
                                state='readonly')
        comboBox['values'] = userList
        if len(userList) > 0:
            comboBox.current(0)
        comboBox.pack()
        # Set up Button for ensure or cancel
        yesBtn = tk.Button(popWin, text='Send', command=sendResultToWinMan)
        noBtn = tk.Button(popWin, text='Cancel', command=popWin.destroy)
        yesBtn.pack(side='left')
        noBtn.pack(side='right')
        if len(userList) == 0:
            yesBtn['state'] = 'disabled'
    
    def putWindowMsg(self, msg):
        self.outputQueue.put(msg)
    
    def getWindowMsg(self):
        return self.inputQueue.get()       
    
    def popUpWindow(self, which, title, msg):
        if which == 'Info':
            # Show info which can be help msg or online msg
            return messagebox.showinfo(title=title, message=msg, parent=self.mainWindow)
        elif which == 'AskQ':
            # Ask Question return yes or no
            return messagebox.askquestion(title=title, message=msg, parent=self.mainWindow)
        elif which == 'AskS':
            # Ask String return String
            return simpledialog.askstring(title=title, prompt=msg, parent=self.mainWindow)
        elif which == 'AskW':
            # Ask Which online user want to talk
            return self._selectUserPopWindow(title, msg)
    
    def closeWindow(self):
        if not self.QuitFlag:
            if self.winType == 'Public':
                self._sendMessage('Q')
            elif self.winType == 'Private':
                self._sendMessage('PQ', PID=self.priID)
            else:
                self._sendMessage('GQ')
        self.mainWindow.destroy()
    
    def runWindow(self):
        # Run Async Output thread
        tOut = Thread(name='WinAsyncOutput', target=self._asyncInsertOutput)
        tOut.daemon = True
        tOut.start()
        # Active main window
        self.mainWindow.mainloop()
        logging.info('Window Close')

"******************************************************************************"

class PriChatWindow(ChatWindow):
    """
    This class is for Pop-Up Private Chatting Window
    Simply Inherit the Chatting Window
    Override the setMainWindow and runWindow
    """
    def __init__(self, parent, privateID, winID, winName, winType, inQueue=Queue(), outQueue=Queue()):
        self.parent = parent
        self.priID = privateID
        self.BgColor = '#33FFAA'
        super().__init__(winID, winName, winType, inQueue, outQueue, self.BgColor)
        
        
    def _setMainWindow(self):
        self.mainWindow = tk.Toplevel(self.parent)
        self.mainWindow.title('Talk with ' + self.winName)
        self.mainWindow.geometry('500x450')
        self.mainWindow['bg'] = self.BgColor
        
    def _setWidget(self):
        super()._setWidget()
        self.onlineLabel['text'] = 'You and {} '.format(self.winName)
    
    def _setMenubar(self):
        def funExit():
            self.QuitFlag = True
            self._sendMessage('PQ', PID=self.priID)
        
        self.menubar = tk.Menu(self.mainWindow)
        
        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label='Get help', command=lambda:self._sendMessage('H'))
        self.helpmenu.add_command(label='Who\'s Online', command=lambda:self._sendMessage('W'), state='disabled')
        self.helpmenu.add_command(label='Talk with...', command=lambda:self._sendMessage('N'), state='disabled')
        self.helpmenu.add_separator()
        self.helpmenu.add_command(label='Exit', command=funExit)
        
        self.menubar.add_cascade(label='Help', menu=self.helpmenu)
        self.mainWindow.config(menu=self.menubar)
    
    def runWindow(self):
        # Run Async Output thread
        tOut = Thread(name='WinAsyncOutput', target=self._asyncInsertOutput)
        tOut.daemon = True
        tOut.start()