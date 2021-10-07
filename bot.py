# TODO: Error handling in general. Currently this class just kinda hopes for the best and lets the language or the socket API throw all the errors
# TODO: Do we want to support having the bot watch multiple channels at once? Currently it can only do one.

import socket
from types import TracebackType
from typing import Iterable, Optional, Type
import command


class Bot:
    _port: int
    _name: bytes
    _server_name: Optional[bytes]
    _socket: socket.SocketIO
    _channel: Optional[bytes]
    _debug: bool

    def __init__(self, name: bytes, port: int, ipv6: bool = True, debug: bool = False) -> None:
        self._name = name
        self._port = port
        self._debug = debug

        addr_family = socket.AF_INET6 if ipv6 else socket.AF_INET
        self._socket = socket.socket(addr_family)

        if debug:
            print(
                f"started bot in debug mode: name: {name.decode()}, port: {port}, using" + "ipv6" if ipv6 else "ipv4")

    def __enter__(self) -> "Bot":
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], exc_traceback: Optional[TracebackType]):
        self.quit("Leaving")

    def connect_to_server(self, server: bytes) -> None:
        self._socket.connect((server, self._port))
        self._send(b"NICK %s" % self._name)
        self._send(b"USER %s 0 * :%s" % (self._name, self._name))

    def join_channel(self, channel: bytes) -> None:
        self._channel = channel
        self._send(b"JOIN #%s" % channel)

    def send_channel_message(self, message: str) -> None:
        self._send(b"PRIVMSG #%s :%r" % (self._channel, message))

    def receive_forever(self) -> None:
        buffer = b""
        while True:
            data = self._socket.recv(2 ** 10)
            buffer += data
            self._handle_command(buffer)

    def _handle_command(self, buffer: bytes) -> None:
        commands = Bot._parse_command(buffer)
        for command in commands:
            self._command_handler(command)

    @staticmethod
    def _parse_command(buffer: bytes) -> Iterable[command.Command]:
        lines = buffer.split(b"\r\n")
        # We'll process all lines but the last, because it may be a partial message the rest of which
        # is still on its way. Sockets aren't magically aware that we're using them to communicate via the
        # IRC protocol, so they may split data that conceptually goes together
        buffer = lines[-1]
        lines = lines[:-1]
        # Also, there could be empty lines, which the IRC RFC specifies must be ignored
        return map(lambda line: command.Command(line), filter(lambda line: line, lines))

    def _command_handler(self, command: command.Command) -> None:
        def ping() -> None:
            if len(command.args) < 1:
                self._reply(b"409 %s :No origin specified" % self._name)
                return
            self._send(b"PONG %s :%s" % (self._server_name, command.args[0]))

        def rpl_myinfo() -> None:
            client_name, server_name, version, user_modes, channel_modes = command.args
            print(b"info: %s" % server_name)
            self._server_name = server_name

        handlers = {
            b"PING": ping,
            b"004": rpl_myinfo,
        }

        if self._debug:
            print(f"in: {command}")

        try:
            handlers[command.command]()
        except KeyError:
            pass  # Ignore unknown commands and replies

    def _reply(self, message: bytes) -> None:
        self._print_debug(message)
        self._socket.sendall(b":%s %s\r\n" % (self._server_name, message))

    def _send(self, message: bytes) -> None:
        self._print_debug(message)
        self._socket.sendall(b"%s\r\n" % message)

    def _print_debug(self, message: bytes):
        if self._debug:
            channel = getattr(self, "_channel", b"{not on any channel}")
            print(f'out: #{channel.decode()}: "{message.decode()}"')

    def quit(self, message: str) -> None:
        message = f"QUIT {message}\r\n"
        self._socket.sendall(message.encode())
        self._socket.close()
