#!/usr/bin/python

import sys
import struct
import requests

########################################################################
#Declarations
########################################################################
def auth(user, host, password):
	payload = {'jid': user, 'host': host, 'token': password}
	r = requests.post('http://127.0.0.1/apiv1/xmpp', data=payload)
	resp = r.json()
	if 'results' in resp:
		code = resp['results']['code']
		if code == 200:
			return True
		elif code == 400:
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
        authResult = auth(u,s,p)
        write(authResult)
    else:
        write(False)
    read()

def write(result):
    if result:
        sys.stdout.write('\x00\x02\x00\x01')
    else:
        sys.stdout.write('\x00\x02\x00\x00')
    sys.stdout.flush()

if __name__ == "__main__":
    try:
        read()
    except struct.error:
        pass