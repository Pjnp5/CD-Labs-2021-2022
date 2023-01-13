"""CD Chat server program."""
import logging
import selectors
import socket
import sys
import fcntl
import os

from src.protocol import CDProto

logging.basicConfig(filename="server.log", level=logging.DEBUG)


class Server:
    """Chat Server process."""
    def __init__(self):
        self.data = {}
        self.selector = selectors.DefaultSelector()
        self.sock = socket.socket()
        self.sock.bind(('localhost', 5555))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.listen(100)
        self.selector.register(self.sock, selectors.EVENT_READ, self.accept)

    def accept(self, sock, mask):
        conn, addr = sock.accept()
        print(f"Client {conn} with address {addr} detected")
        conn.setblocking(False)
        self.selector.register(conn, selectors.EVENT_READ, self.read) #The Server will always be looking for some new reading/writing event

        self.data[conn] = [None] #Dictorary: Key = conn, Value = channels
    
    def read(self, conn, mask):
        try:
            data = CDProto.recv_msg(conn)
            print("Data Pos recieved: ",data)
            if data == None:
                print('closing', conn)
                self.selector.unregister(conn) 
                self.data.pop(conn)  #remove conn from dictorary
                conn.close()
                print(f"{conn} logged out")
            else:
                if data.command ==  "register":

                    pass
                elif (data.command == "join" ):
                    channelList = self.data[conn]  #channelList: list of all the channels for a certain conn
                    if data.channel not in channelList:
                        channelList.append(data.channel)
                        if(None in channelList):    #remove from channelList the inicial channel 'None'
                            channelList.remove(None)
                            self.data[conn] = channelList
                elif(data.command == "message"):    
                    for k,v in self.data.items():    #run all the elements of the dictorary
                        for channel in v:
                            if data.channel == channel:  #compare the values of the dictorary (channelList), with the channel from data
                                CDProto.send_msg(k, data)   #send a message to the data.channel
                        
        except ConnectionError: #this runs something else broke the above code
            print('closing', conn)
            self.selector.unregister(conn) 
            self.data.pop(conn)  #remove conn from dictorary
            conn.close()
            print(f"{conn} logged out")



    def loop(self):
        """Loop indefinetely."""
        while True:
            events = self.selector.select()
            for key, mask in events:               
                callback = key.data
                callback(key.fileobj, mask)

