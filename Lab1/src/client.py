"""CD Chat client program"""
import logging
import socket
import sys
import selectors
import fcntl
import os

from .protocol import CDProto, CDProtoBadFormat

logging.basicConfig(filename=f"{sys.argv[0]}.log", level=logging.DEBUG)


class Client:
    """Chat Client process."""

    def __init__(self, name: str = "Foo"):
        """Initializes chat client."""
        self.name = name     #Registering the client name
        self.channel = None  #Inicially the client starts on the main channel
        self.selector = selectors.DefaultSelector() # creating the selector

    def connect(self):
        """Connect to chat server and setup stdin flags."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("localhost", 5555))
        self.selector.register(self.sock, selectors.EVENT_READ, self.read) #Client waits for something to read
        

    def read(self, conn, mask):
        recieved = CDProto.recv_msg(self.sock)  

        if recieved:
            print(f"\r< {recieved.message}")
        else:
            self.selector.unregister(conn)
            conn.close()

    def keyboard_input(self, stdin, mask):
        """Screening the input keyboard data. """
        user_input = stdin.read().strip()       # lê a mensagem do user e retira o \n do fim 
        
        if user_input == 'exit':  #shutdown the client
            self.sock.close()
            sys.exit(f"Client {self.name} is leaving the chat!")
            
        elif user_input[0:6] == '/join ':
            user_input = user_input[6:]
            join_msg = CDProto.join(user_input)
            CDProto.send_msg(self.sock, join_msg)
            self.channel = user_input
            print(f"Joined to Channel: {self.channel}")
            
        else: #TextMessage
            if self.channel:
                std_msg = CDProto.message(user_input, self.channel)
                CDProto.send_msg(self.sock, std_msg)
            else:
                std_msg = CDProto.message(user_input)
                CDProto.send_msg(self.sock, std_msg)

    def loop(self):
        """Loop indefinetely."""
        origin_file = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, origin_file | os.O_NONBLOCK)
        
        self.selector.register(sys.stdin, selectors.EVENT_READ, self.keyboard_input)

        while True:
            sys.stdout.write('-> ')
            sys.stdout.flush()
            
            for key, mask in self.selector.select():
                callback = key.data
                callback(key.fileobj, mask)