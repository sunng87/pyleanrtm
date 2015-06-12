from pyleanrtm import __version__

UA = 'pyleanrtm/' + __version__

def base_cmd(aid, pid, cmd, op=None):
    data = {}
    if aid is not None:
        data['appId'] = aid
    data['peerId'] = pid
    data['cmd'] = cmd
    if op is not None:
        data['op'] = op
    return data

def direct(aid, pid, msg, cid, transient, receipt):
    cmd = base_cmd(None, pid, 'direct')
    cmd['msg'] = msg
    cmd['cid'] = cid
    if transient:
        cmd['transient'] = True
    if receipt:
        cmd['r'] = True
    return cmd

def session_open(aid, pid):
    cmd = base_cmd(aid, pid, 'session', op='open')
    cmd['ua'] = UA
    return cmd

def session_close(aid, pid):
    cmd = base_cmd(None, pid, 'session', op='close')
    return cmd

def conv_start(aid, pid, m, attrs):
    cmd = base_cmd(None, pid, 'conv', op='start')
    cmd['m'] = m
    cmd['attrs'] = attrs
    return cmd

def conv_add(aid, pid, m, cid):
    cmd = base_cmd(None, pid, 'conv', op='add')
    cmd['m'] = m
    cmd['cid'] = cid
    return cmd

def conv_remove(aid, pid, m, cid):
    cmd = base_cmd(None, pid, 'conv', op='remove')
    cmd['m'] = m
    cmd['cid'] = cid
    return cmd

def ack_for(cmd):
    ack = base_cmd(None, cmd['peerId'], 'ack')
    ack['cid'] = cmd['cid']
    ack['mid'] = cmd['id']
    return ack

def parse_error(cmd):
    if cmd.get('cmd') == 'error':
        return (cmd['code'], cmd['reason'])

    if cmd.get('cmd') == 'ack' and cmd.has_key('code'):
        return (cmd['code'], cmd['reason'])

    return None

class Message(object):
    def __init__(self, cmd):
        self.msg_id = cmd.get('id')
        self.cid = cmd.get('cid')
        self.from_client = cmd.get('fromPeerId')
        self.data = cmd.get('msg')
        self.timestamp = cmd.get('timestamp')

def dispatch_event(cmd, session):
    if session is not None:
        if cmd.get('cmd') == 'conv':
            if cmd.get('op') == 'joined':
                session.on_joined_conversation(cmd.get('cid'), cmd.get('initBy'))
            if cmd.get('op') == 'left':
                session.on_left_conversation(cmd.get('cid'), cmd.get('initBy'))
            if cmd.get('op') == 'members-joined':
                session.on_clients_joined_conversation(cmd.get('cid'), cmd.get('m'), cmd.get('initBy'))
            if cmd.get('op') == 'members-left':
                session.on_clients_left_conversation(cmd.get('cid'), cmd.get('m'), cmd.get('initBy'))
        if cmd.get('cmd') == 'rcp':
            session.on_receipt(self, cmd.get('id'), cmd.get('cid'))
        if cmd.get('cmd') == 'direct':
            session.on_message(self, Message(cmd))
