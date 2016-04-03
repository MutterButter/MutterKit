################################################################
# File: mango.py
# Title: IRC Client Library
# Author: Sorch <sorch@protonmail.ch>
# Version: 0.7a
# Description:
#  An event-based library for connecting to one or multiple IRC rooms
################################################################

################################################################
# License
################################################################
# Copyright 2016 Contributing Authors
# This program is distributed under the terms of the GNU GPL.
#################################################################


#IMPORTS
###


import asyncore, socket
import re
import itertools
import threading
import time
from tools import delay


class ConnMgr(asyncore.dispatcher_with_send):
	def __init__(self):
		self.out_buffer = b''
		self.nick = None
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.ping_re = re.compile('^PING (?P<payload>.*)', re.IGNORECASE)
		self.join_re = re.compile(':(?P<nick>.*?)!\S+\s+?JOIN\s+:\s*#(?P<channel>[-\w]+)')
		self.part_re = re.compile(':(?P<nick>.*?)!\S+\s+?PART\s+#(?P<channel>[-\w]+)')
		self.chanmsg_re = re.compile(':(?P<nick>.*?)!\S+\s+?PRIVMSG\s+#(?P<channel>[-\w]+)\s+:(?P<message>[^\n\r]+)')
		self.registeredRe = re.compile(':(?P<server>.*?)\s+(?:376|422)')
		self.privmsg_re = re.compile(':(?P<nick>.*?)!~\S+\s+?PRIVMSG\s+[^#][^:]+:(?P<message>[^\n\r]+)')
		self.userlist_re = re.compile('^:.* 353 %s (=|@) (?P<chan>.*?) :(?P<names>.*)' %  self.nick)
		self.quit_re = re.compile(':(?P<nick>.*?)!\S+\s+?QUIT\s+.*')
		self.nc_re = re.compile(':(?P<nick>.*?)!\S+\s+?NICK\s+:\s*(?P<newnick>.*)')
		self.kick_re = re.compile('^:([\w\d]*)!(?:~)?([\w\d\@\/\-\.]*)\sKICK\s([\w\d\#\-]*)\s([\w\d]*)\s(?:\:)?(.*)')
		self._channels = None
		self._userlist = {}
		self.mgr = self


	def parseMode(self, user):
		mode = user[0]
		if mode not in["@","&","%", "~", "+"]:
			mode =  " "
		else:
			mode = mode
		name = user.lstrip(mode)
		return name

	def handle_close(self):
		self.close()

	def _patterns(self):
		return (
			(self.ping_re, self._handlePing),
			(self.join_re, self._joinHandler),
			(self.chanmsg_re, self._msgHandler),
			(self.registeredRe, self._handleRegistered),
			(self.privmsg_re, self._handlePrivmsg),
			(self.part_re, self._handlePart),
			(self.userlist_re, self._handleUserList),
			(self.quit_re, self.handle_quit),
			(self.nc_re, self.handle_nc),
			(self.kick_re, self.handle_kick),
		)

	def _send(self, data):
		data = data + "\r\n"
		self.send(data.encode("utf-8"))

	def writeable(self):
		return True


	def handle_kick(self):
		f = self.kick_re.match(self.bd)
		if f:
			kicker = f.group(1).lower()
			chan = f.group(3)
			channel = f.group(3)
			kickee = f.group(4).lower()
			if chan in self._userlist and kickee == self.nick:
				del self._userlist[chan]
				self._channels.remove(channel)
			else:
				if kickee in self._userlist[chan]:
					self._userlist[chan].remove(kickee)


	def _msgHandler(self, nick, channel, message):
		pass

	def _joinHandler(self, nick, channel):
		pass

	def _handlePrivmsg(self, nick, message):
		pass

	def _handlePart(self, nick, channel):
		pass


	def handle_nc(self, nick, newnick):
		nick = nick.lower()
		newnick = newnick.lower()
		for chan in self._channels:
			chan = chan
			if chan in self._userlist:
				if nick in self._userlist[chan]:
					self._userlist[chan].remove(nick)
					self._userlist[chan].append(newnick)
		pass

	def handle_quit(self, nick):
		nick = nick.lower()
		for chan in self._channels:
			chan = chan
			if chan in self._userlist:
				if nick in self._userlist[chan]:
					self._userlist[chan].remove(nick)
		pass

	def _handleUserList(self, chan, names):
		nameslist = list()
		names = names.split(" ")
		ab = itertools.chain(names)
		names = list(ab)
		for name in names:
			if not name:
				continue
			user = self.parseMode(name)
			nameslist.append(user.lower())
		self._updateNames(chan, nameslist)

	def _updateNames(self, chan, names):
		ch = chan
		if ch not in self._userlist: self._userlist[ch] = []
		self._userlist[ch] = names

	def respond(self, message, channel = None, nick = None):
		try:
			message = message.decode("utf-8")
		except:
			message = message
		if channel:
			self._send("PRIVMSG %s :%s" % (channel, message))

	def delayrespond(self, message, channel, d):
		d = int(d)
		try:
			message = message.decode("utf-8")
		except:
			message = message

		@delay(d)
		def ret(channel, message):
			self._send("PRIVMSG %s :%s" % (channel, message))
		ret(channel, message)

	def auth(self):
		self._send("NICK %s" % self.nick)
		self._send("USER %s %s blah :%s" % (self.nick, "a", self.nick))

	def _handlePing(self, payload):
		self._send("PONG %s" % payload)

	def _handleRegistered(self, server):
		print("Registered at %s" % server)
		self._send("MODE %s +B" % self.nick)
		self._send("PRIVMSG NickServ :id %s" % self.password)
		self.registered = True
		self._chanloop()

	def _chanloop(self):
		for chan in self._channels:
			print(">> %s " % chan)
			self.join(chan)

	def join(self, chan):
		self._send("JOIN %s" % chan)
		if not chan in self._channels:
			self._channels.append(chan)

	def part(self, chan):
		self._send("PART %s" % chan)
		if chan in self._channels:
			self._channels.remove(chan)

	def _connect(self, server, port):
		self.connect((server, port))
		self.auth()

	def _run(self, server, port, nick, chans, password):
		self.nick = nick
		self._channels = chans
		self._connect(server, port)
		self.password = password

	def state(self):
		return self._state

	def handle_read(self):
		data = self.recv(3024).decode()
		for d in data.split("\r\n"):
			patterns = self._patterns()
			for pattern, callback in patterns:
				self.bd = d
				match = pattern.match(d)
				if match:
					callback(**match.groupdict())
