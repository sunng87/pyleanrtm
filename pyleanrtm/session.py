from threading import Timer
import time
import itertools

from pyleanrtm.router import RouteManager
from pyleanrtm.protocol.json_protocol import json_protocol
from pyleanrtm.commands import *

from ws4py.client.threadedclient import WebSocketClient
from ws4py.messaging import PingControlMessage

DEFAULT_RETRY_INTERVAL=2
DEFAULT_COMMAND_TIMEOUT=15
DEFAULT_PING_TIMEOUT=400
DEFAULT_PING_INTERVAL=150

class Session(object):
    def __init__(self, client_id, session_mgr):
        self.client_id = client_id
        self.manager = session_mgr
        self.app_id = self.manager.app_id
        manager.sessions[self.client_id] = self
        self.opened = False

    def send_message(self, cid, msg, transient=False, receipt=False, success=None, fail=None):
        cmd = direct(self.app_id, self.client_id, msg, cid, transient, receipt)
        self.manager.send(cmd, success, fail)

    def open(self, success=None, fail=None):
        self.opened = True
        cmd = session_open(self.app_id, self.client_id)
        self.manager.send(cmd, success, fail)

    def close(self, success=None):
        self.opened = False
        cmd = session_close(self.app_id, self.client_id)
        ## remove from self.manager
        self.manager.send(cmd, success, None)
        self.manager.sessions.pop(self.client_id)

    def start_conversation(self, members, attrs, success=None, fail=None):
        cmd = conv_start(self.app_id, self.client_id, members, attrs)
        self.manager.send(cmd, success, fail)

    def add_to_conversation(self, members, cid, success=None, fail=None):
        cmd = conv_add(self.app_id, self.client_id, members, cid)
        self.manager.send(cmd, success, fail)

    def remove_from_conversation(self, members, cid, success=None, fail=None):
        cmd = conv_remove(self.app_id, self.client_id, members, cid)
        self.manager.send(cmd, success, fail)

    def on_joined_conversation(self, cid, by):
        pass

    def on_left_conversation(self, cid, by):
        pass

    def on_message(self, msg):
        pass

    def on_receipt(self, msg_id, cid):
        pass

    def on_clients_joined_conversation(self, cid, m, by):
        pass

    def on_clients_left_conversation(self, cid, m, by):
        pass

class LeanRTMWebSocketClient(WebSocketClient):
    def __init__(self, url, mgr, **kwargs):
        WebSocketClient.__init__(self, url, **kwargs)
        self.mgr = mgr

    def opened(self):
        self.mgr._on_open()

    def received_message(self, msg):
        self.mgr._on_message(msg)

    def closed(self, status, reason):
        self.mgr._on_close()

    def ponged(self):
        self.mgr._on_pong()

    def ping(self):
        self.send(PingControlMessage())

class WebSocketSessionManager(object):
    def __init__(self, app_id, region='cn'):
        self.app_id = app_id
        self.route_manager = RouteManager(app_id, region)
        self.protocol = json_protocol
        self.conn = None
        self.next_try = DEFAULT_RETRY_INTERVAL
        self.last_pong = 0
        self.keep_alive_thread = None
        self.connected = False
        self.pendings = {}
        ## TODO, is this thread-safe?
        self.id_gen = itertools.count(1)
        self.sessions = {}

    def _try_start(self, server):
        conn = LeanRTMWebSocketClient(server, self, protocols=[self.protocol.name])
        conn.connect()
        self.conn = conn

    def start(self):
        self._restart()

    def _connect_success(self, route, secondary):
        self.route_manager.cache(route, secondary)
        self.next_try = DEFAULT_RETRY_INTERVAL
        self.last_pong = time.time()
        self.keep_alive_thread = Timer(DEFAULT_PING_INTERVAL, self.keep_alive)
        self.keep_alive_thread.start()

    def _restart(self):
        while True:
            route = self.route_manager.fetch()
            try:
                print "connecting:", route.server
                self._try_start(route.server)
                self._connect_success(route, False)
                return
            except Exception as e:
                print e
                if route.secondary:
                    try:
                        print "connecting secondary:", route.secondary
                        self._try_start(route.secondary)
                        self._connect_success(route, True)
                        return
                    except:
                        time.sleep(self.next_try)
                        self.next_try *= 2
                else:
                    self.route_manager.invalid_cache()
                    time.sleep(self.next_try)
                    self.next_try *= 2

    def stop(self):
        self._connection_inactive()

    def _connection_inactive(self):
        self.conn.close()
        self.keep_alive_thread.cancel()

    def keep_alive(self):
        if self.last_pong <= time.time() - DEFAULT_PING_TIMEOUT:
            self._connection_inactive()
            return
        self.conn.ping()

    def send(self, cmd, success_cb, failed_cb):
        serial_id = self.id_gen.next()
        cmd['i'] = serial_id

        self.pendings[serial_id] = (success_cb, failed_cb)
        self.__send(cmd)
        pass

    def __send(self, cmd):
        self.conn.send(self.protocol.encode(cmd))

    def _on_open(self):
        self.connected = True
        pass

    def _on_close(self):
        self.connected = False
        pass

    def _on_message(self, m):
        cmd = self.protocol.decode(m)
        if cmd.has_key('i'):
            serial_id = cmd['i']
            if self.pendings.has_key(serial_id):
                success_cb, fail_cb = self.pendings.pop(serial_id)
                error = parse_error(cmd)
                if error:
                    if fail_cb is not None:
                        fail_cb(*error)
                elif success_cb is not None:
                    ## TODO: only expose some of fields
                    success_cb(cmd)
        else:
            ## events
            client_id = cmd.get('peerId')
            if cmd.get('cmd') == 'direct' and cmd.get('fromPeerId') != cmd.get('peerId'):
                self.__send(ack_for(cmd))

            dispatch_event(cmd, self.sessions.get(client_id))
            pass

    def _on_pong(self):
        self.last_pong = time.time()
