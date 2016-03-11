from pyleanrtm import __version__
import messages_pb2

UA = 'pyleanrtm/' + __version__

# ======= protobuf =====

def proto_dumps(d):
    cmd = d.get('cmd')
    f = messages_pb2.GenericCommand()

    f.cmd = messages_pb2.CommandType.Value(cmd)
    if d.get("op"):
        f.op = messages_pb2.OpType.Value(d.get("op").replace("-", "_"))
    if d.get("appId"):
        f.appId = d.get("appId")
    if d.get("peerId"):
        f.peerId = d.get("peerId")
    if d.get('i'):
        f.i = d.get('i')

    submessage_type = getattr(messages_pb2, cmd.capitalize()+"Command")
    submessage = submessage_type()

    for fd in submessage_type.DESCRIPTOR.fields:
        v = d.get(fd.name)
        if v is None: continue
        if fd.type == fd.TYPE_ENUM:
            setattr(submessage, fd.name, fd.enum_type.Value(v))
        elif fd.type == fd.TYPE_MESSAGE:
            ## client won't send these types, skip them for now
            if fd.message_type == messages_pb2.UnreadTuple.DESCRIPTOR:
                pass
            if fd.message_type == messages_pb2.JsonObjectMessage.DESCRIPTOR:
                j = messages_pb2.JsonObjectMessage()
                j.data = json.dumps(v)
                getattr(submessage, fd.name).CopyFrom(j)
            if fd.message_type == messages_pb2.LogItem.DESCRIPTOR:
                pass
        else:
            if fd.label == fd.LABEL_REPEATED:
                getattr(submessage, fd.name).extend(v)
            else:
                setattr(submessage, fd.name, v)

    getattr(f, cmd+"Message").CopyFrom(submessage)
    return f.SerializeToString()

def parse_proto_field(data, fd, recur):
    if fd.label == fd.LABEL_REPEATED and not recur:
        return map(lambda x: parse_proto_field(x, fd, True), data)

    if fd.type == fd.TYPE_ENUM:
        return fd.enum_type.Name(data)
    elif fd.type == fd.TYPE_MESSAGE:
        ## client won't send these types, skip them for now
        if fd.message_type == messages_pb2.UnreadTuple.DESCRIPTOR:
            return data
        if fd.message_type == messages_pb2.JsonObjectMessage.DESCRIPTOR:
            if data.data:
                return json.loads(data.data)
            else:
                return None
        if fd.message_type == messages_pb2.LogItem.DESCRIPTOR:
            if data:
                return {'from': getattr(data,'from'),
                        'data': data.data,
                        'timestamp': data.timestamp,
                        'msgId': data.msgId}
            return None
    else:
        return data


def proto_loads(msg):
    d = {}
    f = messages_pb2.GenericCommand()
    f.ParseFromString(msg)
    cmd = messages_pb2.CommandType.Name(f.cmd)
    d['cmd'] = cmd
    if f.HasField('appId'):
        d['appId'] = f.appId
    if f.HasField('op'):
        d['op'] = messages_pb2.OpType.Name(f.op).replace("_", "-")
    if f.HasField('peerId'):
        d['peerId'] = f.peerId
    if f.HasField('i'):
        d['i'] = f.i

    submessage_type = getattr(messages_pb2, cmd.capitalize()+"Command")
    submessage = getattr(f, cmd+"Message")

    for fd in submessage_type.DESCRIPTOR.fields:
        v = parse_proto_field(getattr(submessage, fd.name), fd, False)
        if v: d[fd.name] = v
    return d

def base_cmd(aid, pid, cmd, op=None):
    data = {}
    if aid is not None:
        data['appId'] = aid
    data['peerId'] = pid
    data['cmd'] = cmd
    if op is not None:
        data['op'] = op
    return data

def wrap_protobuf(f):
    def inner_protobuf(*args):
        cmd_map = f(*args)
        return proto_dumps(cmd_map)
    return inner_protobuf

@wrap_protobuf
def direct(aid, pid, msg, cid, transient, receipt):
    cmd = base_cmd(None, pid, 'direct')
    cmd['msg'] = msg
    cmd['cid'] = cid
    if transient:
        cmd['transient'] = True
    if receipt:
        cmd['r'] = True
    return cmd

@wrap_protobuf
def session_open(aid, pid):
    cmd = base_cmd(aid, pid, 'session', op='open')
    cmd['ua'] = UA
    return cmd

@wrap_protobuf
def session_close(aid, pid):
    cmd = base_cmd(None, pid, 'session', op='close')
    return cmd

@wrap_protobuf
def conv_start(aid, pid, m, attrs):
    cmd = base_cmd(None, pid, 'conv', op='start')
    cmd['m'] = m
    cmd['attrs'] = attrs
    return cmd

@wrap_protobuf
def conv_add(aid, pid, m, cid):
    cmd = base_cmd(None, pid, 'conv', op='add')
    cmd['m'] = m
    cmd['cid'] = cid
    return cmd

@wrap_protobuf
def conv_remove(aid, pid, m, cid):
    cmd = base_cmd(None, pid, 'conv', op='remove')
    cmd['m'] = m
    cmd['cid'] = cid
    return cmd

@wrap_protobuf
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
            session.on_receipt(cmd.get('id'), cmd.get('cid'))
        if cmd.get('cmd') == 'direct':
            session.on_message(Message(cmd))
