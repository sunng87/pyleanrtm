import httplib
import time
import json

from pyleanrtm.error import InvalidArgumentException, AppAccessDisabledException, AppNotFoundOrDisabledException

class RouteRecord(object):
    def __init__(self, addr, ttl, secondary=None):
        self.server = addr
        self.valid_until = time.time() + ttl
        self.secondary = secondary

    def is_valid(self):
        return self.valid_until >= time.time()

class RouteManager(object):
    def __init__(self, app_id, region='cn'):
        if region == 'cn':
            self.host = 'router.g0.push.avoscloud.com'
        elif region == 'us':
            self.host = 'router.a0.push.avoscloud.com'
        else:
            raise InvalidArgumentException('unsupported region')
        self.app_id = app_id
        self.cached_record = None

    def fetch(self):
        if self.cached_record:
            return self.cached_record

        path = '/v1/route?&secure=1&appId=%s' % self.app_id
        conn = httplib.HTTPConnection(self.host)
        conn.request('GET', path)
        r = conn.getresponse()
        if r.status == 200:
            route = json.loads(r.read())
            return RouteRecord(route['server'], route['ttl'], route['secondary'])
        elif r.status == 404:
            raise AppNotFoundOrDisabledException(self.app_id)
        elif r.status == 403:
            raise AppAccessDisabledException(self.app_id)

    def cache(self, record, secondary):
        if secondary:
            record.addr = record.secondary
        self.cached_record = record

    def invalid_cache(self):
        self.cached_record = None
