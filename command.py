from typing import Optional, Sequence


class Error(Exception):
    "Base error class for this module."
    pass


class MissingCommandError(Error):
    "An error raised if an attempt is made to create a command object from a string without a command"
    pass


class EmptyPrefixError(Error):
    "A command started with :, declaring a prefix, but there was actually no prefix"
    pass


class Command:
    "A single IRC command"
    prefix: Optional[bytes]
    command: bytes
    args: Sequence[bytes]
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

        try:
            args = next(parts)
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

        self.prefix = prefix
        self.command = command
        self.args = arguments

    def __str__(self) -> str:
        prefix = f":{self.prefix.decode()}" if self.prefix else ""
        out = f"{prefix} {self.command.decode()}"

        for arg in self.args[:-1]:
            out += f" {arg.decode()}"
        try:
            last = self.args[-1]
            out += f" :{last.decode()}" if self._trailing else f" {last.decode()}"
        except IndexError:
            pass  # Apparently there were no arguments, so we don't have to worry about stringifying them
        return out
