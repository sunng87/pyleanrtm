from threading import Timer
import time

from pyleanrtm.router import RouteManager
from pyleanrtm.protocol.json_protocol import json_protocol

from ws4py.client.threadedclient import WebSocketClient
from ws4py.messaging import PingControlMessage

DEFAULT_RETRY_INTERVAL=2
DEFAULT_COMMAND_TIMEOUT=15
DEFAULT_PING_TIMEOUT=400
DEFAULT_PING_INTERVAL=150

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

class WebSocketConnectionManager(object):
    def __init__(self, app_id, region='cn'):
        self.app_id = app_id
        self.route_manager = RouteManager(app_id, region)
        self.protocol = json_protocol
        self.conn = None
        self.next_try = DEFAULT_RETRY_INTERVAL
        self.last_pong = 0
        self.keep_alive_thread = None

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

    def send(self, cmd):
        self.conn.send(self.protocol.encode(cmd))

    def _on_open(self):
        pass

    def _on_close(self):
        pass

    def _on_message(self, m):
        cmd = self.protocol.decode(m)

    def _on_pong(self):
        self.last_pong = time.time()
