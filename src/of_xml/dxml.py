#! /usr/bin/env python
import sys
import collections
from . import sxml

class Node(object):
	def __init__(self,name,attributes,parent):
		self.name=name
		self.attributes=attributes
		print("Node attributes: %s"%attributes)
		self.children=[]
		self.parent=parent
		if parent:
			self.parent.children.append(self)

class Text(Node):
	def __init__(self,text,parent):
		self.text=text
		Node.__init__(self,"#TEXT",collections.defaultdict(lambda: None),parent)

class Comment(Node):
	def __init__(self,comment,parent):
		self.comment=comment
		Node.__init__(self,"#COMMENT",collections.defaultdict(lambda: None),parent)

EMPTY_TAGS=["area", "base", "basefont", "br", "col", "frame", "hr", "img", "input", "isindex", "link", "meta", "param"]
class DocHandler(sxml.Handler):
	def __init__(self):
		self.doc=Node("#DOCUMENT",collections.defaultdict(lambda: None),None)
		self.nodestack=[]

	def processing_instruction(self,pi,attributes): pass

	def open(self,tag,attributes): 
		tag=tag.lower()
		print("Opening %s"%tag)
		n = Node(tag,attributes,self.nodestack[-1] if len(self.nodestack)>0 else self.doc)
		if tag not in EMPTY_TAGS:
			self.nodestack.append(n)
		print("nodes: %s"%[ n.name for n in self.nodestack])

	
	def empty(self,tag,attributes): 
		tag=tag.lower()
		print("Empty %s"%tag)
		print("Attributes %s"%attributes)
		Node(tag,attributes,self.nodestack[-1] if len(self.nodestack)>0 else self.doc)

	def close(self,tag): 
		tag=tag.lower()
		while self.nodestack[-1].name!=tag:
			print("Closing '%s', and expecting to close '%s'"%(tag,self.nodestack[-1].name))
			self.close(self.nodestack[-1].name)
		print("Closing %s"%tag)
		self.nodestack.pop()
		print("nodes: %s"%[ n.name for n in self.nodestack])

	def text(self,text):
		Text(text,self.nodestack[-1] if len(self.nodestack)>0 else self.doc)

	def cdata(self,text): 
		Text(text,self.nodestack[-1] if len(self.nodestack)>0 else self.doc)

	def comment(self,comment): 
		Comment(comment,self.nodestack[-1] if len(self.nodestack)>0 else self.doc)

def getdocument(src):
	dh = DocHandler()
	p=sxml.Parser(dh)
	p.parse(src)
	return dh.doc
