self.addEventListener("fetch", event => console.log(`[ServiceWorker] Fetch ${event.request.url}`))

const offlineHTML = `

  <!DOCTYPE html>
  <html class="no-js">

  <head>
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <title>Offline</title>
      <meta name="description" content="">
      <meta name="viewport" content="width=device-width, initial-scale=1">
  </head>

  <style>
    body {
      font-family: monospace, sans-serif;
      margin: 0 2em;
      height: 100vh;
      display: grid;
      grid-template-rows: 1fr 1fr;
      background-color: #ffffff;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 200 200'%3E%3Cpolygon fill='%23DCEFFA' fill-opacity='0.48' points='100 0 0 100 100 100 100 200 200 100 200 0'/%3E%3C/svg%3E");
    }

	.message {
	  align-self: flex-end;
	}

    h1 {
      color: #3488db;
      text-align: center;
      align-self: center;
      font-size: 38px;
      font-family: monospace, sans-serif;
      padding: 0;
      margin: 0;
    }

    svg{
      display: block;
      margin: 0;
      padding: 0;
      width: 100%;
    }

    img{
      display:block;
      margin:auto;
    }

    .btn {
      height: 50px;
      display: block;
      margin: 35px;
      background-color: rgb(52, 136, 219);
      line-height: 25px;
      color: #FFF;
      text-decoration: none;
      text-align: center;
      box-shadow: 0 2px 4px 0 rgba(0,0,0,.6);
      font-size: 25px;
      padding: 0 15px;
      font-family: monospace;
      border: 1px solid rgb(25, 123, 220);
      align-self: center;
    }
  </style>

  <body>

  	<div class="message">

	 <?xml version="1.0" encoding="UTF-8" standalone="no"?>
	 <!-- Created with Inkscape (http://www.inkscape.org/) -->

	 <svg
	    xmlns:dc="http://purl.org/dc/elements/1.1/"
	    xmlns:cc="http://creativecommons.org/ns#"
	    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
	    xmlns:svg="http://www.w3.org/2000/svg"
	    xmlns="http://www.w3.org/2000/svg"
	    xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
	    xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
	    width="256"
	    height="256"
	    viewBox="0 0 33.866666 33.866668"
	    version="1.1"
	    id="svg596"
	    inkscape:version="0.92.4 (5da689c313, 2019-01-14)"
	    sodipodi:docname="OSP-1.svg">
	   <defs
	      id="defs590" />
	   <sodipodi:namedview
	      id="base"
	      pagecolor="#1e1e1e"
	      bordercolor="#666666"
	      borderopacity="1.0"
	      inkscape:pageopacity="0.0"
	      inkscape:pageshadow="2"
	      inkscape:zoom="2.8"
	      inkscape:cx="-5.8340039"
	      inkscape:cy="39.466554"
	      inkscape:document-units="px"
	      inkscape:current-layer="layer1"
	      showgrid="false"
	      units="px"
	      borderlayer="true"
	      inkscape:showpageshadow="false"
	      inkscape:pagecheckerboard="true"
	      inkscape:window-width="1920"
	      inkscape:window-height="1028"
	      inkscape:window-x="0"
	      inkscape:window-y="0"
	      inkscape:window-maximized="1" />
	   <g
	      inkscape:label="Layer 1"
	      inkscape:groupmode="layer"
	      id="layer1"
	      transform="translate(0,-263.13333)">
	     <g
	        id="g573"
	        transform="matrix(0.21027836,0,0,0.21027836,-36.47737,256.79739)">
	       <path
	          style="color:#000000;font-style:normal;font-variant:normal;font-weight:normal;font-stretch:normal;font-size:66.07123566px;line-height:1.25;font-family:'Good Times';-inkscape-font-specification:'Good Times';font-variant-ligatures:normal;font-variant-position:normal;font-variant-caps:normal;font-variant-numeric:normal;font-variant-alternates:normal;font-feature-settings:normal;text-indent:0;text-align:start;text-decoration:none;text-decoration-line:none;text-decoration-style:solid;text-decoration-color:#000000;letter-spacing:0px;word-spacing:0px;text-transform:none;writing-mode:lr-tb;direction:ltr;text-orientation:mixed;dominant-baseline:auto;baseline-shift:baseline;text-anchor:start;white-space:normal;shape-padding:0;clip-rule:nonzero;display:inline;overflow:visible;visibility:visible;opacity:1;isolation:auto;mix-blend-mode:normal;color-interpolation:sRGB;color-interpolation-filters:linearRGB;solid-color:#000000;solid-opacity:1;vector-effect:none;fill:#000000;fill-opacity:1;fill-rule:nonzero;stroke:none;stroke-width:1.64930594;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-dasharray:none;stroke-dashoffset:0;stroke-opacity:1;color-rendering:auto;image-rendering:auto;shape-rendering:auto;text-rendering:auto;enable-background:accumulate"
	          d="m 283.65361,90.02901 v 41.26003 h 8.5139 V 98.597679 h 27.08308 v 13.334571 h -20.72423 v 8.35122 h 29.11251 v -0.009 h 0.0435 l 0.009,-30.244779 z"
	          id="path1692"
	          inkscape:connector-curvature="0"
	          sodipodi:nodetypes="ccccccccccccc" />
	       <path
	          style="color:#000000;font-style:normal;font-variant:normal;font-weight:normal;font-stretch:normal;font-size:medium;line-height:normal;font-family:sans-serif;font-variant-ligatures:normal;font-variant-position:normal;font-variant-caps:normal;font-variant-numeric:normal;font-variant-alternates:normal;font-feature-settings:normal;text-indent:0;text-align:start;text-decoration:none;text-decoration-line:none;text-decoration-style:solid;text-decoration-color:#000000;letter-spacing:normal;word-spacing:normal;text-transform:none;writing-mode:lr-tb;direction:ltr;text-orientation:mixed;dominant-baseline:auto;baseline-shift:baseline;text-anchor:start;white-space:normal;shape-padding:0;clip-rule:nonzero;display:inline;overflow:visible;visibility:visible;opacity:1;isolation:auto;mix-blend-mode:normal;color-interpolation:sRGB;color-interpolation-filters:linearRGB;solid-color:#000000;solid-opacity:1;vector-effect:none;fill:#000000;fill-opacity:1;fill-rule:evenodd;stroke:none;stroke-width:1.64930594;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-dasharray:none;stroke-dashoffset:0;stroke-opacity:1;color-rendering:auto;image-rendering:auto;shape-rendering:auto;text-rendering:auto;enable-background:accumulate"
	          d="M 232.29507,90.040286 V 115.16 h 35.50035 v 7.57973 h -11.3932 v 8.54933 h 20.01502 v -25.11972 h -35.50036 v -7.578114 h 34.95434 v -8.55094 z"
	          id="path1694"
	          inkscape:connector-curvature="0"
	          sodipodi:nodetypes="ccccccccccccc" />
	       <path
	          sodipodi:nodetypes="ccccccccccc"
	          inkscape:connector-curvature="0"
	          id="path1696"
	          d="m 180.30863,90.040053 v 41.249677 h 51.98643 v -8.54987 l -43.27016,-0.003 V 98.590957 h 26.77045 v 16.588133 h 8.71369 V 90.040058 Z"
	          style="color:#000000;font-style:normal;font-variant:normal;font-weight:normal;font-stretch:normal;font-size:medium;line-height:normal;font-family:sans-serif;font-variant-ligatures:normal;font-variant-position:normal;font-variant-caps:normal;font-variant-numeric:normal;font-variant-alternates:normal;font-feature-settings:normal;text-indent:0;text-align:start;text-decoration:none;text-decoration-line:none;text-decoration-style:solid;text-decoration-color:#000000;letter-spacing:normal;word-spacing:normal;text-transform:none;writing-mode:lr-tb;direction:ltr;text-orientation:mixed;dominant-baseline:auto;baseline-shift:baseline;text-anchor:start;white-space:normal;shape-padding:0;clip-rule:nonzero;display:inline;overflow:visible;visibility:visible;opacity:1;isolation:auto;mix-blend-mode:normal;color-interpolation:sRGB;color-interpolation-filters:linearRGB;solid-color:#000000;solid-opacity:1;vector-effect:none;fill:#3488db;fill-opacity:1;fill-rule:evenodd;stroke:none;stroke-width:1.64930582;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-dasharray:none;stroke-dashoffset:0;stroke-opacity:1;color-rendering:auto;image-rendering:auto;shape-rendering:auto;text-rendering:auto;enable-background:accumulate" />
	       <path
	          inkscape:connector-curvature="0"
	          id="path1700"
	          d="m 208.90031,110.21179 -10.65974,-7.9027 v 7.9027 7.90323 z"
	          style="opacity:1;vector-effect:none;fill:#ffb600;fill-opacity:1;stroke:none;stroke-width:0.18011644;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-dasharray:none;stroke-dashoffset:0;stroke-opacity:1" />
	       <rect
	          y="122.74821"
	          x="240.0983"
	          height="8.5368242"
	          width="8.5368242"
	          id="rect458"
	          style="opacity:1;vector-effect:none;fill:#ffb600;fill-opacity:1;fill-rule:evenodd;stroke:none;stroke-width:0.29185364;stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4;stroke-dasharray:none;stroke-dashoffset:0;stroke-opacity:1" />
	     </g>
	   </g>
	 </svg>
     <h1>You are offline</h1>
     </div>

    <button class="btn" onClick="window.location.reload();">Retry</button>

  </body>

  </html>

`;

self.addEventListener("fetch", event => {

    event.respondWith(
        fetch(event.request)
        .catch( () => new Response(offlineHTML, { headers : {"Content-Type": "text/html;charset=utf-8"}}))
    );

});
