"""Bounded IRC transport. No durable history or recipient acknowledgment claim."""
import re
import socket
import time
from ..contracts import ContractError,require
from .. import channel_contracts as c


class Frames:
    def __init__(self):self.buffer=b''
    def feed(self,data):
        require(type(data) is bytes and len(data)<=4096)
        self.buffer+=data;require(len(self.buffer)<=8192,'OVERLOADED')
        result=[]
        while b'\r\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\r\n',1)
            require(len(line)+2<=c.MAX_FRAME,'OVERLOADED')
            require(b'\r' not in line and b'\n' not in line and b'\0' not in line)
            try:decoded=line.decode('utf-8','strict')
            except UnicodeError:raise ContractError('INVALID_ARGUMENT') from None
            result.append(decoded)
        require(len(self.buffer)<=c.MAX_FRAME-2,'OVERLOADED')
        require(b'\n' not in self.buffer and b'\r' not in self.buffer[:-1] and b'\0' not in self.buffer)
        return result


def message(line,target,own_nick):
    if ' PRIVMSG ' not in line:return None
    match=re.fullmatch(r':([^ !]+)![^ @]+@[^ ]+ PRIVMSG ([^ ]+) :(.*)',line)
    require(match is not None,'INVALID_ARGUMENT')
    nick,destination,body=match.groups()
    if destination!=target or nick.casefold()==own_nick.casefold():return None
    c.text(body);return nick,body


class IRC:
    def __init__(self,host,port,target,nick):
        require(host=='127.0.0.1' and type(port) is int and 1<=port<=65535,'UNSUPPORTED_PROFILE')
        require(re.fullmatch(r'#[a-z0-9-]{1,30}',target) and re.fullmatch(r'[A-Za-z][A-Za-z0-9-]{0,29}',nick))
        self.socket=socket.create_connection((host,port),timeout=2);self.socket.settimeout(.05)
        self.target,self.nick,self.frames=target,nick,Frames();self.ready=False
        self.socket.sendall(('NICK '+nick+'\r\nUSER '+nick+' 0 * :generated S06 bridge\r\n').encode())
    def receive(self):
        try:data=self.socket.recv(4096)
        except socket.timeout:return []
        require(bool(data),'NOT_AVAILABLE');result=[]
        for line in self.frames.feed(data):
            if line.startswith('PING :'):
                self.socket.sendall(('PONG :'+line[6:]+'\r\n').encode())
            elif re.search(r' 001 '+re.escape(self.nick)+r' ',line):
                self.socket.sendall(('JOIN '+self.target+'\r\n').encode())
            elif re.search(r' 366 '+re.escape(self.nick)+' '+re.escape(self.target)+r' ',line):self.ready=True
            else:
                value=message(line,self.target,self.nick)
                if value is not None:result.append(value)
        return result
    def send(self,text):
        require(self.ready,'NOT_AVAILABLE')
        self.socket.sendall(('PRIVMSG '+self.target+' :'+text+'\r\n').encode())
    def close(self):self.socket.close()
