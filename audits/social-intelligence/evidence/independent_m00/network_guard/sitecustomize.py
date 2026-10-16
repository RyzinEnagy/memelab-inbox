"""Offline verification guard; logs event names only, never destinations or secrets."""
import os
import sys


def offline(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"}:
        with open(os.environ["M00_NETWORK_LOG"], "a", encoding="utf-8") as stream:
            stream.write(event + "\n")
        raise RuntimeError("M00 verification refuses network access")


sys.addaudithook(offline)
