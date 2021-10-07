#!/usr/bin/env python3

# TODO: Error handling in general. Currently this class just kinda hopes for the best and lets the language or the socket API throw all the errors
# TODO: Do we want to support having the bot watch multiple channels at once? Currently it can only do one.

import socket
from types import TracebackType
from typing import Iterable, Optional, Sequence, Tuple, Type
import command


class Bot:
    __port: int
    __name: bytes
    __server_name: Optional[bytes]
    __socket: socket.SocketIO
    __channel: Optional[bytes]

    def __init__(self, name: bytes, port: int, ipv6: bool = True) -> None:
        self.__name = name
        self.__port = port
        addr_family = socket.AF_INET6 if ipv6 else socket.AF_INET
        self.__socket = socket.socket(addr_family)

    def __enter__(self) -> "Bot":
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], exc_traceback: Optional[TracebackType]):
        self.quit("Leaving")

    def connect_to_server(self, server: bytes) -> None:
        self.__socket.connect((server, self.__port))
        message = b"NICK %s\r\nUSER %s 0 * :%s\r\n" % (
            self.__name, self.__name, self.__name)
        self.__socket.sendall(message)

    def join_channel(self, channel: bytes) -> None:
        self.__channel = channel
        message = b"JOIN #%s\r\n" % channel
        self.__socket.sendall(message)

    def send_channel_message(self, message: str) -> None:
        message_bytes = b"PRIVMSG #%s :%s\r\n" % (
            self.__channel, message.encode()
        )
        self.__socket.sendall(message_bytes)

    def receive_forever(self) -> None:
        buffer = b""
        while True:
            data = self.__socket.recv(2 ** 10)
            print(b"data: %s" % data)
            buffer += data
            self.__handle_command(buffer)

    def __handle_command(self, buffer: bytes) -> None:
        commands = Bot.__parse_command(buffer)
        for command in commands:
            self.__command_handler(command)

    @staticmethod
    def __parse_command(buffer: bytes) -> Iterable[command.Command]:
        lines = buffer.split(b"\r\n")
        # We'll process all lines but the last, because it may be a partial message the rest of which
        # is still on its way. Sockets aren's magically aware that we're using them to communicate via the
        # IRC protocol, so they may split data that conceptually goes together
        buffer = lines[-1]
        lines = lines[:-1]
        # Also, there could be empty lines, which the IRC RFC specifies must be ignored
        return map(lambda line: command.Command(line), filter(lambda line: line, lines))

    def __command_handler(self, command: command.Command) -> None:
        def ping() -> None:
            if len(command.args) < 1:
                self.__reply(b"409 %s :No origin specified" % self.__name)
                return
            self.__send(b"PONG %s :%s" % (self.__server_name, command.args[0]))

        def rpl_myinfo() -> None:
            client_name, server_name, version, user_modes, channel_modes = command.args
            print(b"info: %s" % server_name)
            self.__server_name = server_name

        handlers = {
            b"PING": ping,
            b"004": rpl_myinfo,
        }

        try:
            handlers[command.command]()
        except KeyError:
            pass  # Ignore unknown commands and replies

    def __reply(self, message: bytes) -> None:
        self.__socket.sendall(b":%s %s\r\n" % (self.__server_name, message))

    def __send(self, message: bytes) -> None:
        print(b"sending: %s" % message)
        self.__socket.sendall(b"%s\r\n" % message)

    def quit(self, message: str) -> None:
        message = f"QUIT {message}\r\n"
        self.__socket.sendall(message.encode())
        self.__socket.close()


with Bot(b"microbot", 6667, ipv6=True) as bot:
    bot.connect_to_server(b"::1")
    bot.join_channel(b"text")
    bot.send_channel_message("Hello there, I am a bot")
    bot.receive_forever()
