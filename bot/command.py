"""
This module contains the data structures to represent an IRC command
"""

from typing import Optional, Sequence, Tuple
import re


class Error(Exception):
    "Base error class for this module."


class MissingCommandError(Error):
    "An error raised if an attempt is made to create a command object from a string without a command"


class InvalidPrefixError(Error):
    "A command started with `:`, thus having a prefix, but the prefix's format was invalid"


class InvalidArgumentsError(Error):
    "A valid command was given, but its arguments were invalid"


# Anything but an !, one or more, capturing group
nick = br"([^!]+)"
# an !, Anything but an @ sign, one or more, capturing group. The whole thing is optional
name = br"(?:!([^@]+))?"
# an @, Anything at all, one or more, capturing group. The whole thing is optional
host = br"(?:@(.+))?"
PREFIX_REGEX = re.compile(b"%s%s%s" % (nick, name, host))


class Prefix:
    nick: bytes
    name: Optional[bytes]
    host: Optional[bytes]

    def __init__(self, input: bytes) -> None:
        match = PREFIX_REGEX.match(input)
        if match:
            self.nick = match[1]
            try:
                self.name = match[2]
            except KeyError:
                self.name = None
            try:
                self.host = match[3]
            except KeyError:
                self.host = None
        else:
            raise InvalidPrefixError

    def __str__(self) -> str:
        if self.name:
            name = f"!{self.name.decode()}"
        else:
            name = ""
        if self.host:
            host = f"@{self.host.decode()}"
        else:
            host = ""
        return f"{self.nick.decode()}{name}{host}"


class Command:
    "A single IRC command"
    prefix: Optional[Prefix]
    command: bytes
    args: Sequence[bytes]
    _trailing: bool  # used by __str__

    def __init__(self, input: bytes) -> None:
        """
        Create a command by parsing an IRC command bytestring
        Raises `EmptyPrefixError` if the string starts with `:` but has no actual prefix, and
        `MissingCommandError` if the string doesn't have a command
        """
        prefix: Optional[Prefix]
        if input.startswith(b":"):
            self._trailing = True
            # There definitely is a first part, which is at least the :
            parts = iter(input.split(maxsplit=1))

            # And if it's _only_ the :, then there isn't an actual prefix
            prefix = Prefix(next(parts)[1:])

            # Anything left, if anything exists, is still to parse
            input = next(parts, b"")
        else:
            prefix = None

        parts = iter(input.split(maxsplit=1))
        try:
            command = next(parts)
        except StopIteration:
            raise MissingCommandError

        special_parsers = {
            b"352": self._parse_whoreply_args  # RPL_WHOREPLY
        }

        self.prefix = prefix
        self.command = command
        try:
            self.args = special_parsers[command](next(parts))
        except KeyError:
            self.args = self._parse_most_args(next(parts))

    def __str__(self) -> str:
        prefix = f":{self.prefix}" if self.prefix else ""
        out = f"{prefix} {self.command.decode()}"

        for arg in self.args[:-1]:
            if arg:
                out += f" {arg.decode()}"
        try:
            last = self.args[-1]
            if last:
                decode = last.decode()
                out += f" :{decode}" if self._trailing else f" {decode}"
        except IndexError:
            pass  # Apparently there were no arguments, so we don't have to worry about stringifying them
        return out

    def _parse_most_args(self, args: bytes) -> Sequence[bytes]:
        try:
            if args.startswith(b":"):
                self._trailing = True
                arguments = [args[1:]]
            else:
                self._trailing = False
                args_and_trailing = args.split(b" :", 1)
                arguments = args_and_trailing[0].split()
                try:
                    arguments.append(args_and_trailing[1])
                    self._trailing = True
                except:  # This fails if there aren't trailing arguments, in which case we have nothing to append
                    pass
        except StopIteration:
            arguments = []
        return arguments

    # RPL_WHOREPLY is incompatible with the above parser, and in fact violates the IRC message format
    # by having a : before something other than the last parameter (specifically, it's before the second to last)
    # Also, it contains the hostname, which _could_ start with :, for example by being an ipv6 address starting with ::
    # Because this is unacceptable, a more specialized parsing function is necessary
    def _parse_whoreply_args(self, input: bytes) -> Sequence[bytes]:
        import parsers
        from parsers import whitespace, one_of, optional, char, ParseError

        def text(input: bytes) -> Tuple[bytes, bytes]:
            word, rest = parsers.text(input)
            _, rest = whitespace(rest)
            return word, rest

        try:
            nick, rest = text(input)
            _, rest = char(rest, b"#")
            channel, rest = text(rest)
            name, rest = text(rest)
            host, rest = text(rest)
            server, rest = text(rest)
            nick, rest = text(rest)
            hg, rest = one_of(rest, [b"H", b"G"])
            star, rest = optional(rest, lambda x: char(x, b"*"))
            at_plus, rest = optional(rest, lambda x: one_of(x, [b"@", b"+"]))
            _, rest = whitespace(rest)
            _, rest = char(rest, b":")
            hopcount, rest = text(rest)
            _, rest = whitespace(rest)
            realname, rest = text(rest)
            if rest:
                raise InvalidArgumentsError
        except ParseError:
            raise InvalidArgumentsError
        return [nick, channel, name, host, server, nick,
                hg, star if star else b"", at_plus if at_plus else b"", hopcount, realname]
