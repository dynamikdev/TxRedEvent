# A Event Pub-Sub system based on Twisted/Redis

#Copyright (C) 2011  Tartaise Philippe

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.


from sys import exc_info
import traceback
from twisted.internet import reactor, protocol, defer,task
from txredis.protocol import Redis, RedisSubscriber

from zope.interface import Interface,implements

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
try:
    import json
except:
    import simplejson as json

try:
    import cPickle as pickle
except ImportError:
    import pickle   

import re


def OnReady():
	def wrapper(func):
		@defer.inlineCallbacks
		def wrapped(obj,*args,**kwargs):
		    assert hasattr(obj,"initialise") ,"Pas de fonction initialise"
		    yield obj.initialise()
		    result = func(obj,*args,**kwargs)
		    if isinstance(result, defer.Deferred):
			result = yield result
		    defer.returnValue(result)
		return wrapped
	return wrapper

def Initialiseur():
	def wrapper(func):
	    @defer.inlineCallbacks
	    def wrapped(obj,*args,**kwargs):
		if not hasattr(obj,"__Initialiseur_ready"):
		    obj.__Initialiseur_ready = defer.Deferred()
		    try:
			result = func(obj,*args,**kwargs)
		    except Exception,e:
			print "erreur de l'init ",e
			raise e
		    if isinstance(result, defer.Deferred):
		        res = yield result
			
		    else:
			res = result
		    obj.__Initialiseur_ready.callback(res)
		else:
			res = yield obj.__Initialiseur_ready
		defer.returnValue(res)
		
	    return wrapped
	return wrapper    

class IEvent(Interface):
    """Interface de l'evenement"""
    
class Event(object):
    implements(IEvent)
    def __init__(self,type):
        self.type = type
    def __str__(self):
        return str(self.__dict__)
    def __rep__(self):
        return str(self)
    
class IEventPusher(Interface):
    """interface de pusher"""
    def initialise():
        """initialisation"""
    def pushEvent(event,eventkeys):
        """envoi de l'evenement"""
        
class EventPusher(object):
    implements(IEventPusher)
    def __init__(self,encoding="pickle"):
        
        assert encoding in ["json","pickle"],"encoding not supported"
        self.encoding = encoding
    
    def encode(self,val):
        try:
            return {"json":json,
                    "pickle":pickle}[self.encoding].dumps(val)
        except TypeError ,e:
            print val.__dict__
            raise e
    
    def decode(self,val):
        return {"json":json,
         "pickle":pickle}[self.encoding].loads(val)
        
    def encodeKeys(self,keys):
        lkeys = keys.keys()
        lkeys.sort()
        return "|"+"||".join([str(k)+":"+str(keys[k]) for k in lkeys])+"|"
    #def decodekeys(self,encodedKeys):
        #return dict([elem.split(":") for elem in encodedKeys.split("|")[1:-1]])
    
    
    @Initialiseur()
    @defer.inlineCallbacks
    def initialise(self):
        clientCreator = protocol.ClientCreator(reactor, Redis)
        self.redis = yield clientCreator.connectTCP(REDIS_HOST, REDIS_PORT)
        defer.returnValue(True)
        
    @OnReady()
    def pushEvent(self,event,eventKeys={}):
        d= self.redis.publish("event:"+event.type+"#"+self.encodeKeys(eventKeys),self.encode(event))
        return d

class IEventSubscriber(Interface):
    """interface de pusher"""
    
class EventSubscriber(object):
    implements(IEventSubscriber)
    listSubs = {}
    def __init__(self,encoding="pickle"):
        assert encoding in ["json","pickle"],"encoding not supported"
        self.encoding = encoding
        self.subscriber = RedisSubscriber()
        #self.listSubs = {}
        self.regexKeys = re.compile('\w+=\w+')
        self.regexType = re.compile('^event:(\w+)#')
    
    def encode(self,val):
        return {"json":json,
         "pickle":pickle}[self.encoding].dumps(val)
    
    def decode(self,val):
        return {"json":json,
         "pickle":pickle}[self.encoding].loads(val)
    
    #def encodeKeys(self,typeevent,keys):
        #lkeys = keys.keys()
        #lkeys.sort()
        #return "event:"+typeevent+"#*|"+"|*|".join([str(k)+":"+str(keys[k]) for k in lkeys])+"|*"
    #def decodekeys(self,encodedKeys):
        #return dict([elem.split(":") for elem in encodedKeys.split("|")[1:-1] if len(elem)>1 and not re.match("event#"])
    
    @Initialiseur()
    @defer.inlineCallbacks
    def initialise(self):
        MySub = RedisSubscriber
        MySub.messageReceived = self.messageReceived
        clientCreator = protocol.ClientCreator(reactor, MySub)
        self.redis = yield clientCreator.connectTCP(REDIS_HOST, REDIS_PORT)
        defer.returnValue(True)
    @OnReady()
    def subscribe(self,typeevent,eventKeys,objToCall):
        if self.encodeKeys(typeevent,eventKeys) not in self.listSubs.keys():
	    self.listSubs[self.encodeKeys(typeevent,eventKeys)] = []
	self.listSubs[self.encodeKeys(typeevent,eventKeys)].append(objToCall)
	return self.redis.psubscribe(self.encodeKeys(typeevent,eventKeys))
    
    @OnReady()
    def unsubscribe(self,typeevent,eventKeys,objToCall):
        self.listSubs[self.encodeKeys(typeevent,eventKeys)].remove(objToCall)
        if len(self.listSubs[self.encodeKeys(typeevent,eventKeys)]) ==0:
            self.redis.punsubscribe(self.encodeKeys(typeevent,eventKeys))
        return True
    def encodeKeys(self,typeevent,keys):
        lkeys = keys.keys()
        lkeys.sort()
        if len(keys)>0:
            ch= "*|"+"|*|".join([str(k)+":"+str(keys[k]) for k in lkeys])+"|*"
        else :
            ch = "*"
        return "event:"+typeevent+"#"+ch 
    def decodekeys(self,encodedKeys):
        
        return self.regexType.search(encodedKeys).group(1),dict([elem.split(":") for elem in self.regexKeys.findall(encodedKeys)])
        
    def messageReceived(self, channel, message,pattern):
        typevent,keysEvent = self.decodekeys(channel)
        event = self.decode(message)
        try:
            for elem in self.listSubs[pattern]:
                if hasattr(elem,"on"+event.type):
		    #print "appel de la methode associe"
                    task.deferLater(reactor,0,getattr(elem,"on"+event.type),event)
        except Exception,ex :
            print "erreur dans messageReceived de ",self," : ",ex
	    #print self
	    print exc_info()[0],traceback.print_tb(exc_info()[2])
	    print patern
	    print self.listSubs
        return True
    