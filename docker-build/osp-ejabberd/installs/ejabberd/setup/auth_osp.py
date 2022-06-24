########################################################################
# Configuration
########################################################################
protocol = "http"
ospAPIServer = "127.0.0.1:5010"

########################################################################
# Code
########################################################################

import sys, logging, struct
import requests


def auth(user, host, password):
    payload = {"jid": user, "host": host, "token": password}

    global ospAPIServer
    if (
        ospAPIServer != "127.0.0.1"
        and ospAPIServer != "localhost"
        and ospAPIServer != "127.0.0.1:5010"
    ):
        ospAPIServer = host

    r = requests.post(
        protocol + "://" + ospAPIServer + "/apiv1/xmpp/auth", data=payload
    )
    resp = r.json()
    if "results" in resp:
        code = resp["results"]["code"]
        if code == 200:
            return True
        elif code == 400:
            return False
        else:
            return False
    else:
        return False


def isUser(user, host):
    payload = {"jid": user, "host": host}

    global ospAPIServer
    if (
        ospAPIServer != "127.0.0.1"
        and ospAPIServer != "localhost"
        and ospAPIServer != "127.0.0.1:5010"
    ):
        ospAPIServer = host

    r = requests.post(
        protocol + "://" + ospAPIServer + "/apiv1/xmpp/isuser", data=payload
    )
    resp = r.json()
    if "results" in resp:
        code = resp["results"]["code"]
        if code == 200:
            return True
        elif code == 400:
            return False
        else:
            return False
    else:
        return False


def read():
    (pkt_size,) = struct.unpack(">H", sys.stdin.buffer.read(2))
    pkt = sys.stdin.read(pkt_size)
    cmd = pkt.split(":")[0]
    if cmd == "auth":
        u, s, p = pkt.split(":", 3)[1:]
        results = auth(u, s, p)
        write(results)
    elif cmd == "isuser":
        u, s = pkt.split(":", 2)[1:]
        results = isUser(u, s)
        write(results)
    else:
        write(False)


def write(result):
    if result:
        sys.stdout.write("\x00\x02\x00\x01")
    else:
        sys.stdout.write("\x00\x02\x00\x00")
    sys.stdout.flush()


if __name__ == "__main__":
    while True:
        read()
