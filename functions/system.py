from threading import Thread
from functools import wraps
import datetime

from classes.shared import db
from classes import settings
from classes import logs

def asynch(func):

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target = func, args = args, kwargs = kwargs)
        func_hl.start()
        return func_hl

    return async_func

def newLog(logType, message):
    newLogItem = logs.logs(datetime.datetime.now(), str(message), logType)
    db.session.add(newLogItem)
    db.session.commit()
    return True

def rebuildOSPEdgeConf():
    f = open("conf/osp-edge.conf", "w")
    ospEdgeQuery = settings.edgeStreamer.query.filter_by(active=True).all()
    f.write('split_clients "${remote_addr}AAA" $ospedge_node {\n')
    if ospEdgeQuery != []:
        for edge in ospEdgeQuery:
            if edge.port == 80 or edge.port == 443:
                f.write(str(edge.loadPct) + "% " + edge.address + ";\n")
            else:
                f.write(str(edge.loadPct) + "% " + edge.address + ":" + str(edge.port) +";\n" )
    else:
        f.write("100% 127.0.0.1;\n")
    f.write("}")
    f.close()
    return True