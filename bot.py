#!/usr/bin/env python3

# TODO: Error handling in general. Currently this class just kinda hopes for the best and lets the language or the socket API throw all the errors
# TODO: Do we want to support having the bot watch multiple channels at once? Currently it can only do one.

import socket
from types import TracebackType
from typing import Optional, Sequence, Tuple, Type


class Bot:
    __port: int
    __name: bytes
    __server_name: Optional[bytes]
    __socket: socket.SocketIO
    __channel: Optional[bytes]
    __read_buffer: bytes

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
        message = b"NICK %s \r\nUSER %s 0 * :%s\r\n" % (
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
        self.__read_buffer = b""
        while True:
            data = self.__socket.recv(2 ** 10)
            print(b"data: %s" % data)
            self.__read_buffer += data
            self.__handle_command()

    def __handle_command(self) -> None:
        prefix, command, args = self.__parse_command()
        self.__command_handler(prefix, command, args)

    def __parse_command(self) -> Tuple[Optional[bytes], bytes, Sequence[bytes]]:
        lines = self.__read_buffer.split(b"\r\n")
        # We'll process all lines but the last, because it may be a partial message the rest of which
        # is still on its way
        self.__read_buffer = lines[-1]
        lines = lines[:-1]
        for line in lines:
            print(b"line: %s" % line)
            if not line:  # Empty line
                continue

            prefix: Optional[bytes]
            if line.startswith(b":"):  # Has a prefix
                prefix, line = line.split(maxsplit=1)
            else:
                prefix = None

            command, args = line.split(maxsplit=1)
            if args.startswith(b":"):
                arguments = [args[1:]]
            else:
                args_pair = args.split(b" :", 1)
                arguments = args_pair[0].split()
                if len(args_pair) == 2:
                    arguments.append(args_pair[1])

        return prefix, command, arguments

    def __command_handler(self, prefix: Optional[bytes], command: bytes, args: Sequence[bytes]) -> None:
        def ping() -> None:
            if len(args) < 1:
                self.__reply(b"409 %s :No origin specified" % self.__name)
                return
            self.__send(b"PONG %s :%s" % (self.__server_name, args[0]))

        def rpl_myinfo() -> None:
            client_name, server_name, version, user_modes, channel_modes = args
            print(b"info: %s" % server_name)
            self.__server_name = server_name

        handlers = {
            b"PING": ping,
            b"004": rpl_myinfo,
        }

        try:
            handlers[command]()
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
