import os
import logging
from PIL import Image
from pilkit.processors import ProcessorPipeline, ResizeToFit, SmartResize
from flask_security import current_user

from functions import cachedDbCalls

from globals import globalvars

from classes.shared import db
from classes import settings
from classes import panel

log = logging.getLogger('app.functions.database')

# Checks Theme Override Data and if does not exist in override, use Defaultv3's HTML with theme's layout.html
def checkOverride(themeHTMLFile):
    sysSettings = db.session.query(settings.settings).with_entities(settings.settings.systemTheme, settings.settings.maintenanceMode).first()

    # Check for Maintenance Mode
    if sysSettings.maintenanceMode is True:
        if current_user.is_authenticated:
            if current_user.has_role('Admin') is False:
                if "maintenance.html" in globalvars.themeData.get('Override', []):
                    return "themes/" + sysSettings.systemTheme + "/maintenance.html"
                else:
                    return "themes/Defaultv3/maintenance.html"
        else:
            if "maintenance.html" in globalvars.themeData.get('Override', []):
                return "themes/" + sysSettings.systemTheme + "/maintenance.html"
            else:
                return "themes/Defaultv3/maintenance.html"

    # Check if normal theme override exists
    try:
        if themeHTMLFile in globalvars.themeData.get('Override',[]):

            return "themes/" + sysSettings.systemTheme + "/" + themeHTMLFile
        else:
            return "themes/Defaultv3/" + themeHTMLFile
    except:
        return "themes/Defaultv3/" + themeHTMLFile

# Code Modified from https://github.com/Hecsall/favicon-generator
def faviconGenerator(imageLocation):
    originalImage = imageLocation
    directory = globalvars.videoRoot + 'images'

    index = 0

    sizes = [
	#
	#	FileName		LogoSize		BoxSize
	#
		["favicon-16x16",		[16,16],		[16,16]],
		["favicon-32x32",		[32,32],		[32,32]],
		["apple-touch-icon",	[180,180],		[180,180]],
        ["android-chrome-192x192", [192, 192], [192, 192]],
        ["android-chrome-512x512", [512, 512], [512, 512]],

	]

    outfile = os.path.splitext(originalImage)[0] + ".png"

    for size in sizes:
        im = Image.open(originalImage)
        processor = ProcessorPipeline([ResizeToFit(size[1][0], size[1][1])])
        result = processor.process(im)
        background = Image.new('RGBA', size[2], (255, 255, 255, 0))
        background.paste(
			result, (int((size[2][0] - result.size[0]) / 2), int((size[2][1] - result.size[1]) / 2))
		)
        background.save(directory + "/" + size[0] + ".png")
    im = Image.open(originalImage)
    processor = im.resize((16,16), Image.LANCZOS)
    processor.save(directory + "/favicon.ico")
    return 'OK'

def getPagePanels(blueprintPageName, type=0, userID=0):
    panelQuerySorted = None
    if type == 0:
        panelQuery = panel.panelMapping.query.filter_by(pageName=blueprintPageName, panelType=type).all()
        panelQuerySorted = sorted(panelQuery, key=lambda x: x.panelOrder)
    return panelQuerySorted