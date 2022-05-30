# Theme Customization
OSP Supports Custom HTML and CSS theming via creation of another directory under the ```/opt/osp/templates/themes``` directory. 

When theming, you must include at a minimum a layout.html. Use the Default Theme as a template to build your own theme.
Custom CSS can be created under the ```/opt/osp/static/css``` directory under the directory name ```$ThemeName``` and the css file name as ```theme.css```.

Example Format
```
/opt/osp/static/css
	mytheme/
  	theme.css
      
/opt/osp/templates/themes
	mytheme/
  	layout.html
```

Themes also must contain a theme.json file to work properly with OSP.  Any file that will be overridden must be listed in the Override list in the json file.  Any file not listed in the override will use Defaultv3, but with the custom theme's CSS file.

theme.json:
```json
{
  "Name": "Example",
  "Maintainer": "Some User",
  "Version": "1.0",
  "Description": "Description of Theme",
  "Override": ["channelplayer.html"] 
}
```