import json

from pyleanrtm.protocol import BaseProtocol

class JsonProtocol(BaseProtocol):
    name = 'lc-json-1'
    def encode(self, cmd):
        return json.dumps(cmd)

    def decode(self, msg):
        return json.loads(str(msg))

json_protocol = JsonProtocol()
