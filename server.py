import socket
import time
import sys
import threading
import string

from typing import Any, Collection, Dict, List, Optional, Sequence, Set

Socket = socket.socket

class Channel:
    def __init__(self, server: "Server", name: bytes) -> None:
        self.server = server
        self.name = name
        self.members = []

    def add_member(self, client: "Client") -> None:
        self.members.append(client)

    def sendMsg(self, args: [bytes], client: "Client") -> None:
        for members in self.members:
            if members != client:
                members.writeBuffer += b":%s!%s@%s PRIVMSG #%s %s \n\r" % (members.nickname, members.user, members.host, args[0], args[1])


class Client:
    def __init__(self, server: "Server", socket: Socket) -> None:
        self.server = server
        self.socket = socket
        self.user = b""
        self.nickname = b""
        self.realname = b""
        self.channels = []
        self.lastPing = time.time()
        self.readBuffer = b""
        self.writeBuffer = b""

        host, port, _, _ = socket.getpeername()
        self.host = host.encode()
        self.port = port


    #Pings client, if client doesnt respond, diconnected and removed
##    def ping(self, now) -> None:
##        if self.lastPing + 300 == now:
##            print("Disconnecting \n\r")
##            self.disconnect(self)
##        else:
##            data = b"PING :%s" % self.host
##            try:
##                print(f"{data}")
##                self.socket.send(data)
##                data = self.socket.recv(1024)
##                self.lastPing = time.time()
##            except Exception as e:
s##                print(f"Error: {e}")
##                print(f"Disconnecting\n\r")
##                self.disconnect()

    #Removed client object from server
    def disconnect(self) -> None:
        try:
            self.socket.close()
            self.server.remove_client(self)
        except socket.error as e:
            print(f"Socket Error: {e}")

    #checks for new information from server
    def check_msg(self) -> None:
        try:
            self.socket.settimeout(0.5)
            data = self.socket.recv(1024)
            if data:
                ##send data through parser to check for commands or other..
                self.readBuffer += data
                self.parse()
        except socket.error as e:
            data = b""

    #parses and splits lines of data to be handled correctly
    def parse(self) -> None:
        lines = self.readBuffer.splitlines()
        self.readBuffer = b""
        for line in lines:
            if not line:
                continue
            x = line.split(b" ")
            command = x[0].upper()
            args = []
            for y in range(1, len(x)):
                args.append(x[y]) 
            self.handler(command, args)

    #Command handlers
    def handler(self, command: bytes, args: [bytes]) -> None:
        if command == b"NICK" and len(args) > 0:
            oldnickname = self.nickname
            self.nickname = args[0]
            self.setNickname(oldnickname)
            print(f"{self.writeBuffer}")
            self.send_msg()

        if command == b"USER" and len(args) > 0:
            self.user = b"Guest"
            self.realname = args[0]

        if command == b"QUIT":
            msg = args[0]
            self.writeBuffer += b":%s!%s@%s QUIT %s \n\r" % (self.nickname, self.user, self.host, args[0])
            self.send_msg()

        if command == b"JOIN" and len(args) > 0:
            if not self.server.channels:
                self.writeBuffer += b":%s!%s@%s JOIN %s \n\r" % (self.nickname, self.user, self.host, args[0])
                channel = Channel(self.server, args[0])
                self.server.add_channel(channel)
                self.channels.append(channel)
                channel.add_member(self)
                channel.join(args)
            else:
                for channel in self.server.channels:
                    if channel.name == args[0]:
                        self.writeBuffer += b":%s!%s@%s JOIN %s \n\r" % (self.nickname, self.user, self.host, args[0])
                        channel.add_member(self)
                        self.channels.append(channel)
                        channel.join(args)

        if command == b"PRIVMSG" and len(args) > 0:
            for channel in self.channels:
                if channel.name == args[0]:
                    channel.sendMsg(args, self)
            for client in self.server.clients:
                if client.nickname == args[0] and client.nickname != self.nickname:
                    self.writeBuffer += b":%s!%s@%s PRIVMSG %s %s \n\r" % (self.nickname, self.user, self.host, args[0], args[1])

        if command == b"PART" and len(args) > 0:
            try:
                for x in range(0, len(self.channels)):
                    if self.channels[x] == args[0]:
                        self.channels[x].members.remove(self)
                self.channels.remove(args[0])
                self.server.channels.remove(args[0])
            except Exception as e:
                print(f"{e}")
            self.writeBuffer += b":%s!%s@%s PART %s %s\n\r" % (self.nickname, self.user, self.host, args[0], args[1])
            
    #Sets client nickname       
    def setNickname(self, oldnick: bytes) -> None:
        self.writeBuffer += b":%s!%s@%s NICK %s\n\r" % (oldnick, self.user, self.host, self.nickname)

    #Sends info to server
    def send_msg(self) -> None:
        if self.writeBuffer:
            print(f"{self.writeBuffer}")
            try:
                sent = self.socket.send(self.writeBuffer)
            except socket.error as x:
                print(f"Socket Error:{x}")
            self.writeBuffer = b""

class Server:
    def __init__(self) -> None:
        self.host = b"Localhost"
        self.port = 6667
        self.clients = []
        self.channels = []

    #Used to create and bind the socket, then to sets to run
    def start(self) -> None:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        try:
            s.bind(('localhost', 6667,))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
            s.settimeout(5)
        except socket.error as e:
            print(f"Could not bind Port: {e}")
            sys.exit(1)
        s.listen(10)
        print(f"Listening on port 6667")
        try:
            pass
            self.run(s)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    #Creates threads for each main process
    #allows for the server run indefinitely
    def run(self, s: socket) -> None:
        last_ping = time.time()

        threads = []

        try:
            create = threading.Thread(target=self.add_client, args=[s])
            create.start()
            threads.append(create)
        except Exception as e:
            print(f"{e}")

##        ping = threading.Thread(target=self.ping_clients)
##        ping.start()
##        threads.append(ping)

        try:
            send = threading.Thread(target=self.send_messages)
            send.start()
            threads.append(send)  
        except Exception as e:
            print(f"{e}")

        try:
            receive = threading.Thread(target=self.check_messages)
            receive.start()
            threads.append(receive)    
        except Exception as e:
            print(f"{e}")




    #Waits for a connection and tries to add the client to the server    
    def add_client(self, s: socket) -> None:
        while True:
            try:
                conn, addr = s.accept()
                self.clients.append(Client(self, conn))
                print(f"{self.clients}")
                print(f"Accepted connection from {addr[0]}:{addr[1]}.")
                conn = b""
                addr = b""
            except Exception as e:
                try:
                    conn.close()
                except:
                    pass
                
    #Pings all clients within the server, will diconnect if they timeout       
##    def ping_clients(self) -> None:
##        last_ping = time.time()
##        while True:
##            now = time.time()
##            if last_ping + 5 < now:
##                for client in self.clients:
##                    client.ping(now)
##                last_ping = now

    #Remove client details from server
    def remove_client(self, client: "Client") -> None:
        try:
            self.clients.remove(client)
        except Exception:
            print(f"Client: {client} removed")

    #constantly checks for new data/msgs
    def check_messages(self) -> None:
        while True:
            for clients in self.clients:
                try:
                    clients.check_msg()
                except:
                    pass

    #constantly streams data to the server
    def send_messages(self) -> None:
        while True:
            for clients in self.clients:
                try:
                    clients.send_msg()
                except:
                    pass
                
    #gets client object
    def get_client(self, clientName):
        for x in self.clients:
            if x.nickname == clientName :
                return x.nickname

    #adds channel to server
    def add_channel(self, channel: "Channel") -> None:
        self.channels.append(channel)
    
        
def main() -> None:
    server = Server()
    server.start()


if __name__ == "__main__":
    main()
