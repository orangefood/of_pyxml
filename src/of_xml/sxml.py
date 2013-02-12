#! /usr/bin/env python

#
# sxml, Copyright (C) 2011, Robert I. Petersen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import sys
import collections

TAG,ATTRIBUTE,TEXT,PASSTHROUGH=range(4)
OPEN,CLOSE,EMPTY,PROCESSING_INSTRUCTION=range(4)

class _passthrough(object):
	def __init__(self,end,handler):
		self.end=end
		self.handler=handler

class Parser(object):
	def __init__(self,handler):
		self.line=1
		self.col=0
		self._handler=handler
		handler.parser=self
		self._buffer=[]
		self._tag_name=None
		self._attr_name=None
		self._attr={}
		self._quoted_attribute_value=False
		self._mode=TEXT
		self._tag_type=OPEN
		self._passthrough={}
		self.addPassthrough('!--','--',handler.comment)
		self.addPassthrough('![CDATA[',']]',handler.cdata)
		self.addPassthrough('!DOCTYPE','',handler.doctype)
		self._handle_func=[self._handle_tag,self._handle_attribute,self._handle_text,self._handle_passthrough]
		self._tag_func=[self._tag_open,self._tag_close,self._tag_empty,self._tag_processing_instruction]

	def addPassthrough(self,start,end,handler):
		self._passthrough[start]=_passthrough(end,handler)

	def parse(self,src):
		
		while True:
			c=src.read(1)
			if not c: break
			if c=='\n': 
				self.line=self.line+1
				self.col=0
			else:
				self.col=self.col+1
			self._handle_func[self._mode](c)

		if len(self._buffer)>0 and self._mode==TEXT:
			self._handler.text(''.join(self._buffer))
		# Reset
		self._buffer=[]
		self._attr_name=None
		self._attr.clear()
		self._quoted_attribute_value=False
		self._mode=TEXT
		self._tag_type=OPEN

	def _end_tag(self):
		if self._tag_name==None: 
			self._tag_name = ''.join(self._buffer).strip()
			if self._tag_name[0]=='/':
				self._tag_type=CLOSE
				self._tag_name=self._tag_name[1:]
			if self._tag_name[-1]=='/':
				self._tag_name=self._tag_name[:-1]
		if len(self._buffer)>0 and self._buffer[-1]=='/': self._tag_type=EMPTY
		self._tag_func[self._tag_type](self._tag_name)
		self._tag_name=None
		self._buffer=[]
		self._mode=TEXT
		self._tag_type=OPEN

	def _handle_tag(self,c):
		if c=='<':  # we shouldn't see this so close the tag and try again
			self._end_tag()
			self._handle_func[self._mode](c)
#			raise BaseException("Error arroud line %d and column %d"%(self.line,self.col))
		if c=='>': # the end of a tag
			self._end_tag()
		elif c=='?': # a processing instruction
			self._tag_type=PROCESSING_INSTRUCTION
		else:
			tag=''.join(self._buffer).strip()
			# Passthrough tage: comments, CDATA or custom
			if tag in self._passthrough.keys():
				passthrough=self._passthrough[tag]
				self._passthrough_handler=passthrough.handler
				self._passthrough_end=passthrough.end
				self._buffer=[]
				self._mode=PASSTHROUGH
				self._handle_passthrough(c)
			# if the character is not whitespace but the proceeding character is
			# then its an attribute
			elif len(self._buffer)>0 and not c.isspace() and self._buffer[-1].isspace():
				if self._tag_name==None: 
					self._tag_name = ''.join(self._buffer).strip()
				self._buffer=[]
				self._mode=ATTRIBUTE
				self._handle_attribute(c)
			else:
				self._buffer.append(c)

	def _tag_open(self,tag,):
		self._handler.open(tag,collections.defaultdict(lambda: None,self._attr))
		self._attr.clear()

	def _tag_close(self,tag): 
		self._handler.close(tag)

	def _tag_empty(self,tag):
		self._handler.empty(tag,collections.defaultdict(lambda: None,self._attr))
		self._attr.clear()

	def _tag_processing_instruction(self,tag):
		self._handler.processing_instruction(tag,collections.defaultdict(lambda: None,self._attr))
		self._attr.clear()

	def _handle_attribute(self,c):
		if( self._quoted_attribute_value):
			if '"'==c:
				self._close_attribute()
			else:
				self._buffer.append(c)
		else:
			if '='==c:
				self._attr_name=''.join(self._buffer)
				self._buffer=[]
			elif '"'==c:
				self._quoted_attribute_value=True
			elif ' '==c:
				self._close_attribute()
			elif '>'==c:
				if len(self._buffer)>0 and self._buffer[-1]=='/':
					self._buffer=self._buffer[:-1]
					self._tag_type=EMPTY
				self._close_attribute()
				self._handle_tag(c)
			else:
				self._buffer.append(c)

	def _close_attribute(self):
		if self._attr_name==None:
			self._attr_name=''.join(self._buffer)
			self._buffer=[]
		if len(self._attr_name)>0: self._attr[self._attr_name]=''.join(self._buffer)
		self._attr_name=None
		self._buffer=[]
		self._mode=TAG
		self._quoted_attribute_value=False
			

	def _handle_text(self,c):
		if '<'==c:
			if len(self._buffer)>0:
				self._handler.text(''.join(self._buffer))
				self._buffer=[]
			self._mode=TAG
		else:
			self._buffer.append(c)

	def _handle_passthrough(self,c):
		if '>'==c and ''.join(self._buffer[-2:]).endswith(self._passthrough_end):
			l=len(self._passthrough_end)
			buf = self._buffer if l==0 else self._buffer[:-l]
			self._passthrough_handler(''.join(buf))
			self._buffer=[]
			self._mode=TEXT
		else:
			self._buffer.append(c)


class Handler(object):

	def processing_instruction(self,pi,attributes): pass

	def open(self,tag,attributes): pass
	
	def empty(self,tag,attributes): pass

	def close(self,tag): pass

	def text(self,text): pass

	def cdata(self,text): pass
	
	def doctype(self,text): pass

	def comment(self,comment): pass


class PrintHandler(Handler):

	def processing_instruction(self,pi,attributes): 
		print("processing instruction: %s,%s"%(pi,attributes))

	def open(self,tag,attributes):
		print("open: %s,%s"%(tag,attributes))

	def empty(self,tag,attributes):
		print("open: %s,%s"%(tag,attributes))

	def close(self,tag): 
		print("close: %s"%(tag,))

	def text(self,text):
		print("text: %s"%(text,))

	def cdata(self,text):
		print("cdata: %s"%(text,))
	
	def doctype(self,text): 
		print("doctype: %s"%(text,))

	def comment(self,comment):
		print("comment: %s"%(comment,))

class EchoHandler(Handler):
	def processing_instruction(self,pi,attributes): 
		sys.stdout.write('<?')
		sys.stdout.write(pi)
		if len(attributes)>0: sys.stdout.write(' '+' '.join([ i[0]+'="'+i[1]+'"' for i in attributes.items()]))
		sys.stdout.write(">")

	def open(self,tag,attributes):
		sys.stdout.write('<')
		sys.stdout.write(tag)
		if len(attributes)>0: sys.stdout.write(' '+' '.join([ i[0]+'="'+i[1]+'"' for i in attributes.items()]))
		sys.stdout.write(">")

	def empty(self,tag,attributes):
		sys.stdout.write('<')
		sys.stdout.write(tag)
		if len(attributes)>0: sys.stdout.write(' '+' '.join([ i[0]+'="'+i[1]+'"' for i in attributes.items()]))
		sys.stdout.write("/>")

	def close(self,tag): 
		sys.stdout.write('</%s>'%tag)

	def text(self,text):
		sys.stdout.write(text)
	
	def cdata(self,cdata):
		sys.stdout.write("<![CDATA[%s]]>"%cdata)

	def doctype(self,doctype):
		sys.stdout.write("<!DOCTYPE%s>"%s)

	def comment(self,comment):
		sys.stdout.write("<!--%s-->"%(comment,))
