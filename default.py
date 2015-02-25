

import os
import time 
import xbmc
import xbmcgui
import xbmcaddon
from traceback import print_exc

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__cwd__          = __addon__.getAddonInfo('path')
BASE_RESOURCE_PATH = os.path.join( __cwd__, "resources" )
process = os.path.join( BASE_RESOURCE_PATH , "pm.pid")
if os.path.exists(process):
    if xbmcgui.Dialog().yesno("Last.FM playlist generator (partymode)", "Would you like to exit partymode?" ):
        os.remove(process)        
else:
    file( process , "w" ).write( "" )
    xbmc.executebuiltin('XBMC.RunScript(%s)' % os.path.join( __cwd__, "pm.py" ))