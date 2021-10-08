#!/usr/bin/env python3

import bot
import argparse

DEFAULT_HOST = "::1"  # TODO: change this to be the lab VM's IP
DEFAULT_PORT = 6667
DEFAULT_NAME = "microbot"
DEFAULT_CHANNEL = "test"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--host", help="set the server to connect to", default=DEFAULT_HOST)
parser.add_argument("--port", help="set the port to use",
                    type=int, default=DEFAULT_PORT)
parser.add_argument(
    "--name", help="set the name of the bot", default=DEFAULT_NAME)
parser.add_argument(
    "--channel", help="set the channel that the bot will join", default=DEFAULT_CHANNEL)
parser.add_argument("--debug", help="enable debug mode", action="store_true")
parser.add_argument(
    "--ip-version", help='ip version to use. Defaults to "ipv6"', choices=["ipv4", "ipv6"], default="ipv6")

args = parser.parse_args()

try:
    with bot.Bot(args.name.encode(), args.port, ipv6=args.ip_version == "ipv6", debug=args.debug) as b:
        b.connect_to_server(args.host.encode())
        b.join_channel(args.channel.encode())
        b.send_channel_message(f"Hello, I am {args.name}. Try sending !hello or !slap on the channel, or "
                               "sending me a private message.")
        b.receive_forever()
except OSError as e:
    print(f"creating the bot failed. This program will now exit.\n"
          "\tError: {e}")
