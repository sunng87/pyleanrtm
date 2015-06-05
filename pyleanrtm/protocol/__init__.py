class BaseProtocol(object):
    name = None
    def encode(self, cmd): return cmd
    def decode(self, cmd): return cmd
