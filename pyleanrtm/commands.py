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
    cmd = base_cmd(aid, pid, 'direct')
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
    cmd = base_cmd(aid, pid, 'session', op='close')
    return cmd

def conv_start(aid, pid, m, attrs):
    cmd = base_cmd(aid, pid, 'conv', op='start')
    cmd['m'] = m
    cmd['attrs'] = attrs
    return cmd

def conv_add(aid, pid, m, cid):
    cmd = base_cmd(aid, pid, 'conv', op='add')
    cmd['m'] = m
    cmd['cid'] = cid
    return cmd

def conv_remove(aid, pid, m, cid):
    cmd = base_cmd(aid, pid, 'conv', op='remove')
    cmd['m'] = m
    cmd['cid'] = cid
    return cmd

def parse_error(cmd):
    if cmd.get('cmd') == 'error':
        return (cmd['code'], cmd['reason'])

    if cmd.get('cmd') == 'ack' and cmd.has_key('code'):
        return (cmd['code'], cmd['reason'])

    return None
