from typing import Optional, Sequence, Tuple


class Error(Exception):
    "Base error class for this module."
    pass


class MissingCommandError(Error):
    "An error raised if an attempt is made to create a command object from a string without a command"
    pass


class EmptyPrefixError(Error):
    "A command started with :, declaring a prefix, but there was actually no prefix"
    pass


class InvalidArgumentsError(Error):
    "A valid command was given, but its arguments were invalid"


class Command:
    "A single IRC command"
    prefix: Optional[bytes]
    command: bytes
    args: Sequence[Optional[bytes]]
    _trailing: bool  # used by __str__

    def __init__(self, input: bytes) -> None:
        """
        Create a command by parsing an IRC command bytestring
        Raises `EmptyPrefixError` if the string starts with `:` but has no actual prefix, and
        `MissingCommandError` if the string doesn't have a command
        """
        prefix: Optional[bytes]
        if input.startswith(b":"):
            self._trailing = True
            # There definitely is a first part, which is at least the :
            parts = iter(input.split(maxsplit=1))

            # And if it's _only_ the :, then there isn't an actual prefix
            prefix = next(parts)[1:]
            if not prefix:
                raise EmptyPrefixError

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
        prefix = f":{self.prefix.decode()}" if self.prefix else ""
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

    def _parse_most_args(self, args: bytes) -> Sequence[Optional[bytes]]:
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
    def _parse_whoreply_args(self, input: bytes) -> Sequence[Optional[bytes]]:
        import parsers
        from parsers import whitespace, one_of, optional, char, ParseError

        def word(input: bytes) -> Tuple[bytes, bytes]:
            word, rest = parsers.word(input)
            _, rest = whitespace(rest)
            return word, rest

        try:
            nick, rest = word(input)
            _, rest = char(rest, b"#")
            channel, rest = word(rest)
            name, rest = word(rest)
            host, rest = word(rest)
            server, rest = word(rest)
            nick, rest = word(rest)
            hg, rest = one_of(rest, [b"H", b"G"])
            star, rest = optional(rest, lambda x: char(x, b"*"))
            at_plus, rest = optional(rest, lambda x: one_of(x, [b"@", b"+"]))
            _, rest = whitespace(rest)
            _, rest = char(rest, b":")
            hopcount, rest = word(rest)
            _, rest = whitespace(rest)
            realname, rest = word(rest)
            if rest:
                raise InvalidArgumentsError
        except ParseError:
            raise InvalidArgumentsError
        return [nick, channel, name, host, server, nick,
                hg, star, at_plus, hopcount, realname]
