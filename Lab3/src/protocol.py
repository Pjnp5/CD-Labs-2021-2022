"""Protocol for chat server - Computação Distribuida Assignment 1."""
import pickle
import json
from socket import socket
import xml.etree.cElementTree as tree



class Message:
    """Message Type."""
    def __init__(self, command):
        self.command = command
    
class Subscribe_Message(Message):
    """Message to subscribe a topic."""
    def __init__(self, command, type, topic):
        super().__init__(command)
        self.topic = topic
        self.type = type
    
    
    def Dic(self):
        return {"command": self.command, "type": self.type.__str__(), "topic": self.topic}
    def __repr__(self) -> str:
        return f'{{"command": {self.command}, "type": {self.type.__str__()}, "topic": {self.topic}}}'

            

class Publish_Message(Message):
    """Message to publish a topic."""
    def __init__(self, command, type, topic, message):
        super().__init__(command)
        self.type = type
        self.topic = topic
        self.message = message
    
    
    def Dic(self):
        return {"command": self.command, "type": self.type.__str__(), "topic": self.topic, "message": self.message}
    def __repr__(self) -> str:
        return f'{{"command": {self.command}, "type": {self.type.__str__()}, "topic": {self.topic}, "message": {self.message}}}'    


class List_Message(Message):
    """Message to list a topic."""
    def __init__(self, command, type):
        super().__init__(command)
        self.type = type

    def Dic(self):
        return {"command": self.command, "type": self.type.__str__()}
    def __repr__(self) -> str:
        return f'{{"command": {self.command}, "type": {self.type.__str__()}}}'
class List_Response(Message):
    """Message to list topics"""

    def __init__(self, command, List_Topic):
        super().__init__(command)
        self.list_topic = List_Topic

    def Dic(self):
        return {"command": self.command, "type": self.type.__str__(), "topic_list" : self.list_topic}
    def __repr__(self) -> str:
        return f'{{"command": {self.command}, "type": {self.type.__str__()}, "topic_list": {self.list_topic}}}'


class Cancel_Message(Message):
    """Message to subscribe a topic."""
    def __init__(self, command, type,topic):
        super().__init__(command)
        self.topic = topic
        self.type = type
    
    def Dic(self):
        return {"command": self.command, "type": self.type.__str__(), "topic": self.topic}
    def __repr__(self) -> str:
        return f'{{"command": {self.command}, "type": {self.type.__str__()}, "topic": {self.topic}}}'

class MBProto:
    """Computação Distribuida Protocol."""

    @classmethod
    def subscribe(self, type, topic) -> Subscribe_Message:
        return Subscribe_Message("SUBSCRIBE", type, topic)

    @classmethod
    def publish(self, type, topic, message) -> Publish_Message:
        return Publish_Message("PUBLISH", type, topic, message)

    @classmethod
    def list(self, type, list_Topic = None) -> List_Message:
        if list_Topic:
            return List_Response("LIST", list_Topic)
        return List_Message("LIST", type)

    @classmethod
    def unsubscribe(self, type, topic) -> Cancel_Message:
        return Cancel_Message("CANCEL", type, topic)

    @classmethod
    def send_msg(self, conn: socket, command, _type="", topic="", message= None):
        """"""
        if command == "SUBSCRIBE":
            coded_message = self.subscribe(_type,topic)
        elif command == "PUBLISH":
            coded_message = self.publish(_type, topic, message)
        elif  command == "LIST":
            coded_message = self.list(_type, message) 
        elif  command == "CANCEL":
            coded_message = self.unsubscribe(_type, topic)


        if _type == "JSONQueue" or _type.__str__() == "Serializer.JSON":
            coded_message = json.dumps(coded_message.Dic()).encode("utf-8")

        elif _type == "PickleQueue" or _type.__str__() == "Serializer.PICKLE":
            coded_message = pickle.dumps(coded_message.Dic())

        elif _type == "XMLQueue" or _type.__str__() == "Serializer.XML":
            coded_message = coded_message.Dic()
            for key in coded_message:
                coded_message[key] = str(coded_message[key])
            coded_message = tree.Element("mssg", coded_message)
            coded_message = tree.tostring(coded_message)
        
        try:
            header = len(coded_message).to_bytes(2, "big")
            conn.send(header + coded_message)
        except:
            pass


    @classmethod
    def recv_msg(self,conn : socket ,type) :
        try:
            header = conn.recv(2)    # Ler os 2 bytes do header
            header = int.from_bytes(header, 'big')
            if header == 0: return 
            elif header >= 2**16: raise MBProtoBadFormat(header)
            recv_msg = conn.recv(header) # Ler a mensagem
            if recv_msg:
                try:
                    msg = recv_msg.decode('utf-8')
                    msg = json.loads(msg)
                except:
                    try:
                        msg = pickle.loads(recv_msg)
                    except:
                        msg = tree.fromstring(recv_msg.decode("utf-8"))
                        msg = msg.attrib

                command = msg["command"]
                if command == "SUBSCRIBE":
                    _type = msg["type"]
                    topic = msg["topic"]
                    return self.subscribe(_type,topic).Dic() 

                elif command == "PUBLISH":
                    _type = msg["type"]
                    topic = msg["topic"]
                    recv_message = msg["message"]
                    return self.publish(_type ,topic ,recv_message).Dic()
                    
                elif command == "LIST":
                    _type = msg["type"]
                    if msg["topic_list"]:
                        return self.list(_type, msg["topic_list"]).Dic()
                    return self.list(_type).Dic()

                elif command == "CANCEL":
                    _type = msg["type"]
                    topic = msg["topic"]
                    return self.unsubscribe(_type,topic).Dic()
        except:
            raise MBProtoBadFormat()



class MBProtoBadFormat(Exception):
    """Exception when source message is not CDProto."""

    def __init__(self, original_msg: bytes=None) :
        """Store original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self._original.decode("utf-8")
