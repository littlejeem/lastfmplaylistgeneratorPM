"""
	Script for generating smart playlists based on a seeding track and last.fm api
	Created by: ErlendSB
"""

import os
import random
import httplib, urllib, urllib2
import sys, time
import threading, thread
import xbmc, xbmcgui, xbmcaddon
from urllib import quote_plus, unquote_plus
import re
from os.path import exists
from os import remove
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__settings__ = xbmcaddon.Addon(id='script.lastfmplaylistgeneratorPM')
__addonversion__ = __settings__.getAddonInfo('version')
__cwd__          = __settings__.getAddonInfo('path')

def log(message):
    xbmc.log(msg=message)
class MyPlayer( xbmc.Player ) :
	countFoundTracks = 0
	addedTracks = []
	currentSeedingTrack = 0
	firstRun = 0
	dbtype = 'sqlite3'
	timeStarted = time.time()
	SCRIPT_NAME = "LAST.FM Playlist Generator"
	
	allowtrackrepeat =  __settings__.getSetting( "allowtrackrepeat" )
	preferdifferentartist = __settings__.getSetting( "preferdifferentartist" )
	numberoftrackstoadd = ( 1, 3, 5, 10, )[ int( __settings__.getSetting( "numberoftrackstoadd" ) ) ]
	delaybeforesearching= ( 2, 10, 30, )[ int( __settings__.getSetting( "delaybeforesearching" ) ) ]
	limitlastfmresult= ( 50, 100, 250, )[ int( __settings__.getSetting( "limitlastfmresult" ) ) ]
	timer = None


	#apiPath = "http://ws.audioscrobbler.com/2.0/?api_key=71e468a84c1f40d4991ddccc46e40f1b"
	apiPath = "http://ws.audioscrobbler.com/2.0/?api_key=3ae834eee073c460a250ee08979184ec"
	
	def __init__ ( self ):
		if not os.path.exists(xbmc.translatePath("special://userdata/advancedsettings.xml")):
			self.dbtype = 'sqlite3'
		else:
			from xml.etree.ElementTree import ElementTree
			advancedsettings = ElementTree()
			advancedsettings.parse(xbmc.translatePath("special://userdata/advancedsettings.xml"))
			settings = advancedsettings.getroot().find("musicdatabase")
			if settings is not None:
				for setting in settings:
					if setting.tag == 'type':
						self.dbtype = setting.text
			else:
				self.dbtype = 'sqlite3'
		xbmc.Player.__init__( self )
		xbmc.PlayList(0).clear()
		self.firstRun = 1
		BASE_RESOURCE_PATH = os.path.join( __cwd__, "resources" )
		process = os.path.join( BASE_RESOURCE_PATH , "pm.pid")
		removeauto('lastfmplaylistgeneratorpm')
		addauto("if os.path.exists('" + os.path.normpath(process).replace('\\','\\\\') + "'):#lastfmplaylistgeneratorpm\n\tos.remove('" + os.path.normpath(process).replace('\\','\\\\') + "')","lastfmplaylistgeneratorpm")
		xbmc.executebuiltin("Notification(" + self.SCRIPT_NAME+",Start by playing a song)")
	
	def startPlayBack(self):
		print "[LFM PLG(PM)] onPlayBackStarted started"
		if xbmc.Player().isPlayingAudio() == True:
			currentlyPlayingTitle = xbmc.Player().getMusicInfoTag().getTitle()
			print "[LFM PLG(PM)] " + currentlyPlayingTitle + " started playing"
			currentlyPlayingArtist = xbmc.Player().getMusicInfoTag().getArtist()
			self.countFoundTracks = 0
			if (self.firstRun == 1):
				self.firstRun = 0
				#print "firstRun - clearing playlist"
				album = xbmc.Player().getMusicInfoTag().getAlbum()
				cache_name = xbmc.getCacheThumbName(os.path.dirname(xbmc.Player().getMusicInfoTag().getURL()))
				print "[LFM PLG(PM)] Playing file: %s" % xbmc.Player().getMusicInfoTag().getURL()
				thumb = "special://profile/Thumbnails/Music/%s/%s" % ( cache_name[:1], cache_name, )
				duration = xbmc.Player().getMusicInfoTag().getDuration()
				fanart = ""
				listitem = self.getListItem(currentlyPlayingTitle,currentlyPlayingArtist,album,thumb,fanart,duration)
				xbmc.PlayList(0).clear()
				#xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Playlist.Clear", "params": { "playlistid": 0 }, "id": 1}')
				xbmc.executebuiltin('XBMC.ActivateWindow(10500)')
				xbmc.PlayList(0).add(url= xbmc.Player().getMusicInfoTag().getURL(), listitem = listitem)
				#trackPath = xbmc.Player().getMusicInfoTag().getURL()
				#xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Playlist.Add", "params": { "item": {"file": "%s"}, "playlistid": 0 }, "id": 1}' % trackPath)
				self.addedTracks += [xbmc.Player().getMusicInfoTag().getURL()]
			#print "Start looking for similar tracks"
			self.fetch_similarTracks(currentlyPlayingTitle,currentlyPlayingArtist)

	def onPlayBackStarted(self):
		print "[LFM PLG(PM)] onPlayBackStarted waiting:  " + str(self.delaybeforesearching) +" seconds"
		if (self.timer is not None and self.timer.isAlive()):
			self.timer.cancel()
			
		self.timer = threading.Timer(self.delaybeforesearching,self.startPlayBack)
		self.timer.start()

	def fetch_similarTracks( self, currentlyPlayingTitle, currentlyPlayingArtist ):
		apiMethod = "&method=track.getsimilar&limit=" + str(self.limitlastfmresult)

		# The url in which to use
		Base_URL = self.apiPath + apiMethod + "&artist=" + urllib.quote_plus(currentlyPlayingArtist) + "&track=" + urllib.quote_plus(currentlyPlayingTitle)
		#print Base_URL
		WebSock = urllib.urlopen(Base_URL)  # Opens a 'Socket' to URL
		WebHTML = WebSock.read()            # Reads Contents of URL and saves to Variable
		WebSock.close()                     # Closes connection to url

		#xbmc.executehttpapi("setresponseformat(openRecordSet;<recordset>;closeRecordSet;</recordset>;openRecord;<record>;closeRecord;</record>;openField;<field>;closeField;</field>)");
		#print WebHTML
		similarTracks = re.findall("<track>.+?<name>(.+?)</name>.+?<match>(.+?)</match>.+?<artist>.+?<name>(.+?)</name>.+?</artist>.+?</track>", WebHTML, re.DOTALL )
		random.shuffle(similarTracks)
		foundArtists = []
		countTracks = len(similarTracks)
		print "[LFM PLG(PM)] Count: " + str(countTracks)
		for similarTrackName, matchValue, similarArtistName in similarTracks:
			#print "Looking for: " + similarTrackName + " - " + similarArtistName + " - " + matchValue
			similarTrackName = similarTrackName.replace("+"," ").replace("("," ").replace(")"," ").replace("&quot","''").replace("&amp;","and")
			similarArtistName = similarArtistName.replace("+"," ").replace("("," ").replace(")"," ").replace("&quot","''").replace("&amp;","and")
			json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": { "properties": ["title", "artist", "album", "file", "thumbnail", "duration", "fanart"], "limits": {"end":1}, "sort": {"method":"random"}, "filter": { "and":[{"field":"title","operator":"contains","value":"%s"},{"field":"artist","operator":"contains","value":"%s"}] } }, "id": 1}' % (similarTrackName, similarArtistName)) 
			json_query = unicode(json_query, 'utf-8', errors='ignore')
			json_response = simplejson.loads(json_query)
			# separate the records
			if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('songs'):
				count = 0
				for item in json_response['result']['songs']:
					count += 1
					artist = ""
					if (len(item["artist"]) > 0):
						artist = item["artist"][0]
					trackTitle = item["title"]
					album = item["album"]
					trackPath = item["file"]
					thumb = item["thumbnail"]
					duration = int(item["duration"])
					fanart = item["fanart"]
					log("[LFM PLG(PM)] Found: " + str(trackTitle) + " by: " + str(artist))
					if ((self.allowtrackrepeat == "true" or self.allowtrackrepeat == 1) or (trackPath not in self.addedTracks)):
						if ((self.preferdifferentartist != "true" and self.preferdifferentartist != 1) or (eval(matchValue) < 0.2 and similarArtistName not in foundArtists)):
							listitem = self.getListItem(trackTitle,artist,album,thumb,fanart,duration)
							xbmc.PlayList(0).add(url=trackPath, listitem=listitem)
							#xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Playlist.Add", "params": { "item": {"file": "%s"}, "playlistid": 0 }, "id": 1}' % trackPath)
							self.addedTracks += [trackPath]
							xbmc.executebuiltin("Container.Refresh")
							self.countFoundTracks += 1
							if (similarArtistName not in foundArtists):
								foundArtists += [similarArtistName]

				if (self.countFoundTracks >= self.numberoftrackstoadd):
					break
			
		if (self.countFoundTracks == 0):
			time.sleep(3)
			#self.firstRun = 1
			log("[LFM PLG(PM)] None found")
			xbmc.executebuiltin("Notification(" + self.SCRIPT_NAME+",No similar tracks were found)")
			return False
			
		xbmc.executebuiltin('SetCurrentPlaylist(0)')
		
	def getListItem(self, trackTitle, artist, album, thumb, fanart,duration):
		listitem = xbmcgui.ListItem(trackTitle)
		if (fanart == ""):
			cache_name = xbmc.getCacheThumbName( str(artist) )
			fanart = "special://profile/Thumbnails/Music/%s/%s" % ( "Fanart", cache_name, )
		listitem.setProperty('fanart_image',fanart)
		listitem.setInfo('music', { 'title': trackTitle, 'artist': artist, 'album': album, 'duration': duration })
		listitem.setThumbnailImage(thumb)
		#log("[LFM PLG(PM)] Fanart:%s" % fanart)
		return listitem

def addauto(newentry, scriptcode):
	autoexecfile = xbmc.translatePath('special://home/userdata/autoexec.py')
	#autoexecfile = "special://masterprofile/autoexec.py"
	if exists(autoexecfile):
		fh = open(autoexecfile)
		lines = []
		for line in fh.readlines():
			lines.append(line)
		lines.append("import time" + "#" + scriptcode + "\n")
		lines.append("time.sleep(2)" + "#" + scriptcode + "\n")
		lines.append(newentry + "#" + scriptcode + "\n")
		fh.close()
		f = open(autoexecfile, "w")
		if not "import xbmc\n" in lines:
			f.write("import xbmc" + "#" + scriptcode + "\n")
		if not "import os\n" in lines:
			f.write("import os" + "#" + scriptcode + "\n")
		f.writelines(lines)
		f.close()
	else:
		f = open(autoexecfile, "w")
		f.write("import time" + "#" + scriptcode + "\n")
		f.write("time.sleep(2)" + "#" + scriptcode + "\n")
		f.write("import os" + "#" + scriptcode + "\n")
		f.write("import xbmc" + "#" + scriptcode + "\n")
		f.write(newentry + "#" + scriptcode + "\n")
		f.close()

def removeauto(scriptcode):
	autoexecfile = xbmc.translatePath('special://home/userdata/autoexec.py')
	#autoexecfile = "special://masterprofile/autoexec.py"
	if exists(autoexecfile):
		fh = open(autoexecfile)
		lines = [ line for line in fh if not line.strip().endswith("#" + scriptcode) ]
		fh.close()
		f = open(autoexecfile, "w")
		f.writelines(lines)
		f.close()
		
BASE_RESOURCE_PATH = os.path.join( __cwd__, "resources" )

process = os.path.join( BASE_RESOURCE_PATH , "pm.pid")
p=MyPlayer()
while(1):
	if os.path.exists(process):
		if (xbmc.abortRequested):
			os.remove(process)
			print "[LFM PLG(PM)] deleting pid"
		xbmc.sleep(500)
	else:
		break