import socket
import sys

class Server:
    def __init__(self) -> None:
        Host = None
        Port = 50007
        s = None

    def start(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 50007))
            s.listen(1)
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                while True:
                    data = conn.recv(1024)
                    if not data: break
                    conn.sendall(data)
            

    



def main() -> None:
    server = Server()
    server.start()








if __name__ == "__main__":
    main()
