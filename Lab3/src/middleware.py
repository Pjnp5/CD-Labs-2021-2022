"""Middleware to communicate with PubSub Message Broker."""
from collections.abc import Callable
from enum import Enum
import json
import pickle
from typing import Any
import socket
import selectors
from xml.etree import cElementTree
from src.protocol import MBProto


class MiddlewareType(Enum):
    """Middleware Type."""

    CONSUMER = 1
    PRODUCER = 2


class Queue:
    """Representation of Queue interface for both Consumers and Producers."""

    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        """Create Queue."""
        self.topic = topic
        self._type = _type
        self.type_msg = str(self.__class__.__name__)


        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("localhost", 5000))
        
        type_msg = json.dumps({"Serializer": str(self.__class__.__name__)}).encode('utf-8')
        header = len(type_msg).to_bytes(2, "big")

        self.sock.send(header + type_msg)

        self.sock.setblocking(True)

        if self._type==MiddlewareType.CONSUMER:
            self.subscribe(topic)

    def subscribe(self, topic):
        MBProto.send_msg(self.sock,'SUBSCRIBE', self.type_msg, topic)

    def push(self, value):
        """Sends data to broker."""
        MBProto.send_msg(self.sock, "PUBLISH", self.type_msg , self.topic, value)

    def pull(self):
        """Receives (topic, data) from broker.
        Should BLOCK the consumer!"""

        data = MBProto.recv_msg(self.sock, self.type_msg)

        if data:
            return data["topic"], data["message"]
        else:
            return None, None

    def list_topics(self, callback: Callable):
        """Lists all topics available in the broker."""
        MBProto.send_msg('LIST', self.type_msg)

    def cancel(self):
        """Cancel subscription."""
        MBProto.send_msg('CANCEL', self.type_msg, self.topic)


class JSONQueue(Queue):
    """Queue implementation with JSON based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):  
        super().__init__(topic, _type)
    
    def pull(self):
        return super().pull()
     
    def push(self, value):
        return super().push(value) 

    def list_topics(self, callback: Callable):
        return super().list_topics(callback)

    def cancel(self):
        return super().cancel()


class XMLQueue(Queue):
    """Queue implementation with XML based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        super().__init__(topic, _type)
        
    def pull(self):
        return super().pull()
     
    def push(self, value):
        return super().push(value) 

    def list_topics(self, callback: Callable):
        return super().list_topics(callback)
        
    def cancel(self):
        return super().cancel()


class PickleQueue(Queue):
    """Queue implementation with Pickle based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        super().__init__(topic, _type)
        
    def pull(self):
        return super().pull()
     
    def push(self, value):
        return super().push(value) 

    def list_topics(self, callback: Callable):
        return super().list_topics(callback)
        
    def cancel(self):
        return super().cancel() 
