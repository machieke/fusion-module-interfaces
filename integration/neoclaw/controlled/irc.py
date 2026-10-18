"""Declared channel fixture: initialization opens no socket; ingress is empty."""
def start_irc(channel, server, port, user): return True
def getLastMessage(): return ''
def send_message(message): raise RuntimeError('CONTROLLED_CHANNEL_SEND_UNSUPPORTED')
