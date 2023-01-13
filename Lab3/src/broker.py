"""Message Broker"""
import enum
import json
import socket
from typing import Dict, List, Any, Tuple
import selectors
from src.protocol import MBProto


class Serializer(enum.Enum):
    """Possible message serializers."""

    JSON = 0
    XML = 1
    PICKLE = 2


class Broker:
    """Implementation of a PubSub Message Broker."""

    def __init__(self):
        """Initialize broker."""
        self.canceled = False
        self._host = "localhost"
        self._port = 5000
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self._host, self._port))
        self.sock.listen(100)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, selectors.EVENT_READ, self.accept)

        # dictionaries
        self.topics_Dic = set()         # set dos tópicos
        self.userSerializerDic = {}     # socket(pub | sub) : serializer
        self.subtopicsDic = {}          # topic : [(address, serializer)]
        self.topicMessagesDic = {}      # topic : last message


    def accept(self, sock, mask):
        conn, addr = sock.accept()
        print(f"Client {conn} with address {addr} detected")
        conn.setblocking(False)

        header = conn.recv(2)                        
        header = int.from_bytes(header, "big")  
        info = conn.recv(header).decode('UTF-8')
        
        if info:
            if json.loads(info)["Serializer"] == 'JSONQueue':
                self.userSerializerDic[conn] = Serializer.JSON
            elif json.loads(info)["Serializer"] == 'PickleQueue':
                self.userSerializerDic[conn] = Serializer.PICKLE
            elif json.loads(info)["Serializer"] == 'XMLQueue':
                self.userSerializerDic[conn] = Serializer.XML

        self.selector.register(conn, selectors.EVENT_READ, self.read)

    def read(self,conn, mask):
        try:
            if conn in self.userSerializerDic:
                if self.userSerializerDic[conn] == Serializer.JSON:
                    recv_msg = MBProto.recv_msg(conn,type="JSONQueue")
                elif self.userSerializerDic[conn] == Serializer.PICKLE:
                    recv_msg = MBProto.recv_msg(conn,type="PickleQueue")
                elif self.userSerializerDic[conn] == Serializer.XML:
                    recv_msg = MBProto.recv_msg(conn,type="XMLQueue")

                if recv_msg:
                    command = recv_msg["command"]
                    if command == 'SUBSCRIBE':
                        topic = recv_msg["topic"]
                        self.subscribe(topic, conn, self.userSerializerDic[conn])
                    elif command == 'PUBLISH':
                        topic = recv_msg["topic"]
                        message = recv_msg["message"]
                        self.put_topic(topic,message)
                        for _topic in self.subtopicsDic.keys():
                            if (topic).startswith(_topic):
                                for subTopic in self.subtopicsDic[_topic]:
                                    MBProto.send_msg(subTopic[0], command, self.userSerializerDic[conn], topic, message)
                    elif command == 'LIST':
                        topic = recv_msg["topic"]
                        list = self.list_topics()
                        MBProto.send_msg(conn, command, self.userSerializerDic[conn],topic,list)
                        
                    elif command == 'CANCEL':
                        topic = recv_msg["topic"]
                        self.unsubscribe(topic, conn)
                else:
                    pass
        except ConnectionError:
            print('closing', conn)
            self.unsubscribe("", conn)
            self.selector.unregister(conn)
            conn.close()
   


    def list_topics(self) -> List[str]:
        """Returns a list of strings containing all topics containing values."""
        return list(self.topicMessagesDic.keys())

    def get_topic(self, topic):
        """Returns the currently stored value in topic."""
        if topic in self.topics_Dic:
            return self.topicMessagesDic[topic]
        return None

    def put_topic(self, topic, value):
        """Store in topic the value."""
        if topic in self.topicMessagesDic:
            self.topicMessagesDic.update({topic: value})
        else:
            self.topicMessagesDic[topic] = value

        self.topics_Dic.add(topic)     
        print(f'\n{topic} has a new message: {value}')

    def list_subscriptions(self, topic: str) -> List[Tuple[socket.socket, Serializer]]:
        """Provide list of subscribers to a given topic."""
        if topic in self.subtopicsDic.keys():
            return self.subtopicsDic[topic]
        return None


    def subscribe(self, topic: str, address: socket.socket, _format: Serializer = None):
        """Subscribe to topic by client in address."""
        
        self.topics_Dic.add(topic)
        if address in self.userSerializerDic:
            self.userSerializerDic.update({address: _format})
        else:
            self.userSerializerDic[address] = _format

        if topic in self.subtopicsDic:
            self.subtopicsDic[topic].append((address, _format))
        else: 
            self.subtopicsDic[topic] = [(address, _format)] 

        for prev_topic in self.topics_Dic:
            if prev_topic in topic and prev_topic != topic and prev_topic in self.subtopicsDic:
                    [self.subtopicsDic[topic].append(sub_topic) for sub_topic in self.subtopicsDic[prev_topic]]
            if topic in prev_topic and prev_topic != topic:
                self.subtopicsDic[prev_topic].append((address, _format))
            print(f'{address} subscribed the topic {topic}')
            
        if topic in self.topicMessagesDic:
        
            last_msg = self.topicMessagesDic[topic]

            if last_msg:
                MBProto.send_msg(address, "PUBLISH", self.userSerializerDic[address],topic, last_msg)

    def unsubscribe(self, topic, address):
        """Unsubscribe to topic by client in address."""

        if topic in self.subtopicsDic:
            Serializer = self.userSerializerDic[address]
            self.subtopicsDic[topic].remove((address, Serializer))

        print(f'{address} unsubscribed the topic {topic}')       

    def run(self):
        """Run until canceled."""

        while not self.canceled:
            events = self.selector.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
