from globals import globalvars

from classes.shared import db
from classes import settings

# Checks Theme Override Data and if does not exist in override, use Defaultv2's HTML with theme's layout.html
def checkOverride(themeHTMLFile):
    try:
        if themeHTMLFile in globalvars.themeData.get('Override',[]):
            sysSettings = db.session.query(settings.settings).with_entities(settings.settings.systemTheme).first()
            return "themes/" + sysSettings.systemTheme + "/" + themeHTMLFile
        else:
            return "themes/Defaultv2/" + themeHTMLFile
    except:
        return "themes/Defaultv2/" + themeHTMLFile