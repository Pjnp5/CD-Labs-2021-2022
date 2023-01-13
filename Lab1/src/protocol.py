"""Protocol for chat server - Computação Distribuida Assignment 1."""
from email import message
import json
from datetime import datetime
from socket import socket


class Message:
    """Message Type."""
    def __init__(self, command):
        self.command = command
    
class JoinMessage(Message):
    """Message to join a chat channel."""
    def __init__(self, command, new_channel):
        super().__init__(command)
        self.channel = new_channel
    
    def __str__(self):
        return f"{{\"command\": \"{self.command}\", \"channel\": \"{self.channel}\"}}"

class RegisterMessage(Message):
    """Message to register username in the server."""
    def __init__(self, command, user):
        super().__init__(command)
        self.user = user
        
    def __str__(self):
        return f"{{\"command\": \"{self.command}\", \"user\": \"{self.user}\"}}"
    
class TextMessage(Message):
    """Message to chat with other clients."""
    def __init__(self, command, message, channel):
        super().__init__(command)
        self.message = message
        self.channel = channel
    def __str__(self):
        if self.channel == None:
            return f"{{\"command\": \"{self.command}\", \"message\": \"{self.message}\", \"ts\": {int(datetime.now().timestamp())}}}"
        else:
            return f"{{\"command\": \"{self.command}\", \"message\": \"{self.message}\", \"channel\": \"{self.channel}\", \"ts\": {int(datetime.now().timestamp())}}}"


class CDProto:
    """Computação Distribuida Protocol."""

    @classmethod
    def register(cls, username: str) -> RegisterMessage:
        """Creates a RegisterMessage object."""
        return RegisterMessage("register", username)


    @classmethod
    def join(cls, channel: str) -> JoinMessage:
        """Creates a JoinMessage object."""
        return JoinMessage("join", channel)

    @classmethod
    def message(cls, message: str, channel: str = None) -> TextMessage:
        """Creates a TextMessage object."""
        return TextMessage("message", message, channel)

    @classmethod
    def send_msg(cls, connection: socket, msg: Message):
        """Sends through a connection a Message object."""
        data = bytes(msg.__str__(),encoding="utf-8") 
        header = len(data)
        header = header.to_bytes(2, "big")
        if len(data) >= 2**16: raise CDProtoBadFormat
        connection.sendall(header + data)
        # msgJSON=bytes(msg.__str__(),encoding="utf-8")
        # nrBytes=len(msgJSON).to_bytes(2,'big')
        # if(len(msgJSON)>pow(2,16)):
        #     raise CDProtoBadFormat(msgJSON)
        # connection.sendall(nrBytes+msgJSON)

    @classmethod
    def recv_msg(cls, connection: socket) -> Message:
        header = int.from_bytes(connection.recv(2),"big")  #See if the header exists
        # if not head_tmp:
        #     raise ConnectionError()
        recieved_message =  connection.recv(header).decode('utf-8') # recieving the message
        if(recieved_message!=""):
            try:
                message = json.loads(recieved_message)
            except json.decoder.JSONDecodeError:
                raise CDProtoBadFormat

            if message["command"] == "register":
                #user = message["user"]
                return CDProto.register(message["user"])
                
            elif message["command"] == "join":
                #print(message)
                #channel = message["channel"]
                return CDProto.join(message["channel"])
                
            elif message["command"] == "message":
                #recieved_msg = message["message"]
                if "channel" in message:    #verify if the message is for the main channel or another
                    channel = message["channel"]
                    recieved_msg = CDProto.message(message["message"], channel)
                    return recieved_msg
                else:
                    recieved_msg = CDProto.message(message["message"])
                    return recieved_msg


class CDProtoBadFormat(Exception):
    """Exception when source message is not CDProto."""

    def __init__(self, original_msg: bytes=None) :
        """Store original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self._original.decode("utf-8")
