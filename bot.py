#!/usr/bin/env python3

# TODO: Error handling in general. Currently this class just kinda hopes for the best and lets the language or the socket API throw all the errors
# TODO: Do we want to support having the bot watch multiple channels at once? Currently it can only do one.

import socket
from types import TracebackType
from typing import Optional, Type


class Bot:
    _port: int
    _name: str
    _socket: socket.SocketIO
    _channel: Optional[str]

    def __init__(self, name: str, port: int, ipv6: bool = True) -> None:
        self._name = name
        self._port = port
        addr_family = socket.AF_INET6 if ipv6 else socket.AF_INET
        self._socket = socket.socket(addr_family)

    def __enter__(self) -> "Bot":
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], exc_traceback: Optional[TracebackType]):
        self.quit("Leaving")

    def connect_to_server(self, server: str) -> None:
        self._socket.connect((server, self._port))
        message = (f"NICK {self._name}\r\n"
                   f"USER {self._name} 0 * : {self._name}\r\n")
        self._socket.sendall(message.encode())

    def join_channel(self, channel: str) -> None:
        self._channel = channel
        message = f"JOIN #{channel}\r\n"
        self._socket.sendall(message.encode())

    def send_channel_message(self, message: str) -> None:
        message = f"PRIVMSG #{self._channel} :{message}\r\n"
        self._socket.sendall(message.encode())

    def quit(self, message: str) -> None:
        message = f"QUIT {message}\r\n"
        self._socket.sendall(message.encode())
        self._socket.close()


with Bot("microbot", 6667, ipv6=True) as bot:
    bot.connect_to_server("::1")
    bot.join_channel("text")
    bot.send_channel_message("Hello there, I am a bot")
