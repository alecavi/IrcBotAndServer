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

        host, port = socket.getpeername()
        self.host = host.encode()
        self.port = port

    def ping(self, now) -> None:
        if self.lastPing + 300 < now:
            print(f"Disconnecting")
            self.disconnect()
            return
        else:
            data = ""
            try:
                self.socket.send(data.encode())
                data = self.socket.recv(1024)
                self.lastPing = time.time()
            except Exception:
                print(f"Disconnecting")
                self.disconnect()

    def disconnect(self) -> None:
        self.socket.close()
        self.server.remove_client(self)

    def check_msg(self) -> None:
        try:
            data = self.socket.recv(1024)
        except socket.error as e:
            data = b""
        if data:
            ##send data through parser to check for commands or other..
            self.readBuffer += data
            self.parse()

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

    def handler(self, command: bytes, args: [bytes]) -> None:
        print(f"{command}, {args}")
        if command == b"NICK" and len(args) > 0:
            oldnickname = self.nickname
            self.nickname = args[0]
            self.setNickname(oldnickname)
            print(f"{self.writeBuffer}")
            self.send_msg()
        elif command == b"USER" and len(args) > 0:
            self.user = b"Guest"
            self.realname = args[0]
        elif command == b"QUIT":
            msg = args[0]
            self.writeBuffer += b":%s!%s@%s QUIT %s\n\r" % (self.nickname, self.user, self.host, args[0])
            print(f"{self.writeBuffer}")
            self.send_msg()
        if command == b"JOIN" and len(args) > 0:
            self.writeBuffer += b":%s!%s@%s JOIN %s\n\r" % (self.nickname, self.user, self.host, args[0])
            channel = Channel(self.server, args[0])
            self.server.channels.append(channel)
            self.channels.append(channel)
            channel.members.append(self)
            self.send_msg()
        elif command == b"PRIVMSG" and len(args) > 0:
            self.writeBuffer += b":%s!%s@%s PRIVMSG %s :%s\n\r" % (self.nickname, self.user, self.host, args[0], args[1])
            
    def setNickname(self, oldnick: bytes) -> None:
        self.writeBuffer += b":%s!%s@%s NICK %s\n\r" % (oldnick, self.user, self.host, self.nickname)
        
    
  
    def send_msg(self) -> None:
        if self.writeBuffer is not b"\n\r":
            print(f"{self.writeBuffer}")
            try:
                sent = self.socket.send(self.writeBuffer)
            except socket.error as x:
                print(f"{x}")
                self.disconnect()
            self.writeBuffer = b"\n\r"

class Server:
    def __init__(self) -> None:
        self.host = b"Localhost"
        self.port = 6667
        self.clients = []
        self.channels = []
        
    def start(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('localhost', 6667))
        except socket.error as e:
            print(f"Could not bind Port: {e}")
            sys.exit(1)
        s.listen(1)
        print(f"Listening on port 6667")
        try:
            self.run(s)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


    def run(self, s: socket) -> None:
        last_ping = time.time()

        threads = []
        
        create = threading.Thread(target=self.add_client, args=[s])
        create.start()
        threads.append(create)

        ping = threading.Thread(target=self.ping_clients)
        ping.start()
        threads.append(ping)

        send = threading.Thread(target=self.send_messages)
        send.start()
        threads.append(send)

        receive = threading.Thread(target=self.check_messages)
        receive.start()
        threads.append(receive)
        
    def add_client(self, s: socket) -> None:
        while True:
            print(f"Waiting for Client\n\r")
            conn, addr = s.accept()
            try:
                self.clients.append(Client(self, conn))
                print(f"Accepted connection from {addr[0]}:{addr[1]}.")
            except Exception as e:
                print(f"could not add client to list: {e}")
                try:
                    conn.close()
                except Exception:
                    pass
            
    def ping_clients(self) -> None:
        last_ping = time.time()
        while True:
            now = time.time()
            if last_ping + 5 < now:
                for client in self.clients:
                    client.ping(now)
                last_ping = now

    def remove_client(self, client: "Client") -> None:
        try:
            self.clients.remove(client)
        except Exception:
            print(f"Client: {client} removed")

    def check_messages(self) -> None:
        while True:
            for client in self.clients:
                client.check_msg()

    def send_messages(self) -> None:
        while True:
            for client in self.clients:
                client.send_msg()

    def get_client(self, clientName):
        for x in self.clients:
            if x.nickname == clientName :
                return x.nickname

def main() -> None:
    server = Server()
    server.start()


if __name__ == "__main__":
    main()
