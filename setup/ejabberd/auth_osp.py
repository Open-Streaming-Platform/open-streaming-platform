#!/usr/bin/python

########################################################################
#Setup
########################################################################

import sys, logging, struct
import requests

sys.stderr = open('/var/log/ejabberd/extauth_err.log', 'a')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='/var/log/ejabberd/extauth.log',
                    filemode='a')

logging.info('extauth script started, waiting for ejabberd requests')

class EjabberdInputError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def auth(user, host, password):
    payload = {'jid': user, 'host': host, 'token': password}
    r = requests.post('http://127.0.0.1/apiv1/xmpp', data=payload)
    resp = r.json()
    if 'results' in resp:
        code = resp['results']['code']
        if code == 200:
            return True
        elif code == 400:
            logging.debug("Wrong User of Password for user: %s@%s" % (user, host))
            return False
        else:
            return False
    else:
        return False

def read():
    (pkt_size,) = struct.unpack('>H', sys.stdin.read(2))
    pkt = sys.stdin.read(pkt_size)
    cmd = pkt.split(':')[0]
    if cmd == 'auth':
        u, s, p = pkt.split(':', 3)[1:]
        logging.debug('user:' + u)
        logging.debug('host:' + s)
        logging.debug('pass:' + p)
        results = auth(u,s,p)
        write(results)
    else:
        write(False)

def write(result):
    if result:
        sys.stdout.write('\x00\x02\x00\x01')
    else:
        sys.stdout.write('\x00\x02\x00\x00')
    sys.stdout.flush()

if __name__ == "__main__":
    while True:
        try:
            read()
        except Exception as e:
            logging.debug(e)