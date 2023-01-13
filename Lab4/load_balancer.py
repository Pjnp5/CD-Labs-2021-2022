# coding: utf-8
import socket
import selectors
import signal
import logging
import argparse
import time


# configure logger output format
logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',datefmt='%m-%d %H:%M:%S')
logger = logging.getLogger('Load Balancer')


# used to stop the infinity loop
done = False

sel = selectors.DefaultSelector()

policy = None
mapper = None



# implements a graceful shutdown
def graceful_shutdown(signalNumber, frame):  
    logger.debug('Graceful Shutdown...')
    global done
    done = True


# n to 1 policy
class N2One:
    def __init__(self, servers):
        self.servers = servers  

    def select_server(self):
        return self.servers[0]

    def update(self, *arg):
        pass


# round robin policy
class RoundRobin:
    def __init__(self, servers):
        self.servers = servers
        self.round_robin = 0

    def select_server(self):
        server = self.servers[self.round_robin]

        if self.round_robin < len(self.servers) - 1:
            self.round_robin = self.round_robin + 1
        else:
            self.round_robin = 0

        #self.round_robin=(self.round_robin + 1) % len(self.servers)

        return server
    
    def update(self, *arg):
        pass


# least connections policy
class LeastConnections:
    def __init__(self, servers):
        self.servers = servers
        self.conns_counter = {} #server: n_conns_active

    def select_server(self):
        server_to_send = self.servers[0]
        for server in self.servers:
            if(not self.conns_counter.get(server)):
                self.conns_counter.update({server: 0})

            if(self.conns_counter.get(server) < self.conns_counter.get(server_to_send)):
                server_to_send = server

        self.conns_counter.update({server_to_send: self.conns_counter.get(server) + 1})
        
        return server_to_send

    def update(self, *arg):
        # arg[0] = server conn
        self.conns_counter.update({arg[0]: self.conns_counter.get(arg[0]) - 1})


# least response time
class LeastResponseTime:
    def __init__(self, servers):
        self.servers = servers
        self.avg_time = {} #server: [avg_time, n_conn_recv]
        self.conns_start_time = {} #server: start_time1, start_time2...
        self.count = 0
        for server in self.servers:
            if(not self.avg_time.get(server)):
                self.avg_time.update({server: [0, 0]})
                self.conns_start_time.update({server: []})

    def select_server(self):
        #print(self.avg_time)
        server_to_send = self.servers[0]
        if self.avg_time.get(server_to_send)[0] == 0:
            server_to_send = self.servers[self.count]

            self.avg_time.get(server_to_send)[1] = self.avg_time.get(server_to_send)[1] + 1
            if self.count < len(self.servers) - 1:
                self.count = self.count + 1
            else:
                self.count = 0
        else:
            for server in self.servers:
                print(server, server_to_send)
                if(self.avg_time.get(server)[0] < self.avg_time.get(server_to_send)[0]):
                    print("Aqui")
                    server_to_send = server

                elif(self.avg_time.get(server)[0] == 0 and self.avg_time.get(server_to_send)[0] == 0):
                    if(self.avg_time.get(server_to_send)[1] > self.avg_time.get(server)[1]):
                        server_to_send = server

                    self.conns_start_time.get(server_to_send).append(time.time())
                    print("Server com append 1: ",server_to_send, self.conns_start_time.get(server_to_send))

                    self.avg_time.get(server_to_send)[1] = self.avg_time.get(server_to_send)[1] + 1
                    return server_to_send
            
            self.conns_start_time.get(server_to_send).append(time.time())
            print("Server com append 2: ",server_to_send, self.conns_start_time.get(server_to_send))

            self.avg_time.get(server_to_send)[1] = self.avg_time.get(server_to_send)[1] + 1
            return server_to_send


        
        self.conns_start_time.get(server_to_send).append(time.time())
        print("Server com append: ",server_to_send, self.conns_start_time.get(server_to_send))

        self.avg_time.get(server_to_send)[1] = self.avg_time.get(server_to_send)[1] + 1
        return server_to_send

    def update(self, *arg):
        #print("here: ", arg[0], self.conns_start_time.get(arg[0]))

        if self.conns_start_time.get(arg[0])[0]:
            final_time = time.time() - self.conns_start_time.get(arg[0])[0]
            self.conns_start_time.get(arg[0]).pop(0)
            #print("\nhello: ", self.conns_start_time.get(arg[0]))
            avg_time = (self.avg_time.get(arg[0])[0] * (self.avg_time.get(arg[0])[1] -1) + final_time) / (self.avg_time.get(arg[0])[1])
            self.avg_time.update({arg[0]: [avg_time, self.avg_time.get(arg[0])[1]]})
            print("\navg_time: ", self.avg_time)

            
        


POLICIES = {
    "N2One": N2One,
    "RoundRobin": RoundRobin,
    "LeastConnections": LeastConnections,
    "LeastResponseTime": LeastResponseTime
}

class SocketMapper:
    def __init__(self, policy):
        self.policy = policy
        self.map = {}
                               #
    def add(self, client_sock, upstream_server):
        client_sock.setblocking(False)
        sel.register(client_sock, selectors.EVENT_READ, read)
        upstream_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream_sock.connect(upstream_server)
        upstream_sock.setblocking(False)
        sel.register(upstream_sock, selectors.EVENT_READ, read)
        logger.debug("Proxying to %s %s", *upstream_server)
        self.map[client_sock] =  upstream_sock

    def delete(self, sock):
        sel.unregister(sock)
        sock.close()
        if sock in self.map:
            self.map.pop(sock)

    def get_sock(self, sock):
        for client, upstream in self.map.items():
            if upstream == sock:
                return client
            if client == sock:
                return upstream
        return None
    
    def get_upstream_sock(self, sock):
        return self.map.get(sock)

    def get_all_socks(self):
        """ Flatten all sockets into a list"""
        return list(sum(self.map.items(), ())) 

def accept(sock, mask):
    client, addr = sock.accept()
    logger.debug("Accepted connection %s %s", *addr)
    mapper.add(client, policy.select_server())

def read(conn,mask):
    data = conn.recv(4096)
    if len(data) == 0: # No messages in socket, we can close down the socket
        mapper.delete(conn)
    else:
        mapper.get_sock(conn).send(data)


def main(addr, servers, policy_class):
    global policy
    global mapper

    # register handler for interruption 
    # it stops the infinite loop gracefully
    signal.signal(signal.SIGINT, graceful_shutdown)

    policy = policy_class(servers)
    mapper = SocketMapper(policy)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(addr)
    sock.listen()
    sock.setblocking(False)

    sel.register(sock, selectors.EVENT_READ, accept)

    try:
        logger.debug("Listening on %s %s", *addr)
        while not done:
            events = sel.select(timeout=1)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
                
    except Exception as err:
        logger.error(err)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pi HTTP server')
    parser.add_argument('-a', dest='policy', choices=POLICIES)
    parser.add_argument('-p', dest='port', type=int, help='load balancer port', default=8080)
    parser.add_argument('-s', dest='servers', nargs='+', type=int, help='list of servers ports')
    args = parser.parse_args()
    
    servers = [('localhost', p) for p in args.servers]
    
    main(('127.0.0.1', args.port), servers, POLICIES[args.policy])
