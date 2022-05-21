(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
module.exports={
  "name": "videojs-theater-mode",
  "version": "1.1.0",
  "description": "Adds a class the video.js container that can be used to put your video into \"theater mode\"",
  "main": "dist/videojs-theater-mode.cjs.js",
  "module": "dist/videojs-theater-mode.es.js",
  "generator-videojs-plugin": {
    "version": "5.0.0"
  },
  "scripts": {
    "build": "npm run clean; npm run sass; npm run build-dist; cp -r fonts dist/",
    "sass": "mkdir -p dist/ && ./node_modules/.bin/node-sass --output-style compact ./src/videojs.theaterMode.scss dist/videojs.theaterMode.css",
    "build-dist": "mkdir -p dist/ && ./node_modules/.bin/browserify ./src/videojs.theaterMode.js -o dist/videojs.theaterMode.js",
    "clean": "rm -rf dist/"
  },
  "keywords": [
    "videojs",
    "videojs-plugin",
    "theater mode"
  ],
  "author": "Jon <jon@jgubman.com>",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/jgubman/videojs-theater-mode"
  },
  "vjsstandard": {
    "ignore": [
      "dist",
      "docs",
      "test/dist",
      "test/karma.conf.js"
    ]
  },
  "files": [
    "CONTRIBUTING.md",
    "dist/",
    "docs/",
    "fonts/",
    "index.html",
    "scripts/",
    "src/",
    "test/"
  ],
  "dependencies": {
    "global": "^4.3.2",
    "video.js": "^5.2.1"
  },
  "devDependencies": {
    "babelify": "^6.3.0",
    "browserify": "^11.1.0",
    "browserify-shim": "^3.8.10",
    "node-sass": "^3.4.2"
  },
  "browserify": {
    "transform": [
      "babelify",
      "browserify-shim"
    ]
  },
  "browserify-shim": {
    "video.js": "global:videojs"
  }
}

},{}],2:[function(require,module,exports){
(function (global){
'use strict';

Object.defineProperty(exports, '__esModule', {
  value: true
});

var _createClass = (function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ('value' in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; })();

var _get = function get(_x, _x2, _x3) { var _again = true; _function: while (_again) { var object = _x, property = _x2, receiver = _x3; _again = false; if (object === null) object = Function.prototype; var desc = Object.getOwnPropertyDescriptor(object, property); if (desc === undefined) { var parent = Object.getPrototypeOf(object); if (parent === null) { return undefined; } else { _x = parent; _x2 = property; _x3 = receiver; _again = true; desc = parent = undefined; continue _function; } } else if ('value' in desc) { return desc.value; } else { var getter = desc.get; if (getter === undefined) { return undefined; } return getter.call(receiver); } } };

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { 'default': obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError('Cannot call a class as a function'); } }

function _inherits(subClass, superClass) { if (typeof superClass !== 'function' && superClass !== null) { throw new TypeError('Super expression must either be null or a function, not ' + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

var _videoJs = (typeof window !== "undefined" ? window['videojs'] : typeof global !== "undefined" ? global['videojs'] : null);

var _videoJs2 = _interopRequireDefault(_videoJs);

var _packageJson = require('../package.json');

var Button = _videoJs2['default'].getComponent('Button');
var defaults = { className: 'theater-mode' };
var componentName = 'theaterModeToggle';

// Cross-compatibility for Video.js 5 and 6.
var registerPlugin = _videoJs2['default'].registerPlugin || _videoJs2['default'].plugin;

/**
 * Button to add a class to passed in element that will toggle "theater mode" as defined
 * in app's CSS (larger player, dimmed background, etc...)
 */

var TheaterModeToggle = (function (_Button) {
  _inherits(TheaterModeToggle, _Button);

  function TheaterModeToggle(player, options) {
    _classCallCheck(this, TheaterModeToggle);

    _get(Object.getPrototypeOf(TheaterModeToggle.prototype), 'constructor', this).call(this, player, options);
    this.controlText('Toggle theater mode');
  }

  _createClass(TheaterModeToggle, [{
    key: 'buildCSSClass',
    value: function buildCSSClass() {
      if (document.getElementById(this.options_.elementToToggle).classList.contains(this.options_.className)) {
        return 'vjs-theater-mode-control-close ' + _get(Object.getPrototypeOf(TheaterModeToggle.prototype), 'buildCSSClass', this).call(this);
      } else {
        return 'vjs-theater-mode-control-open ' + _get(Object.getPrototypeOf(TheaterModeToggle.prototype), 'buildCSSClass', this).call(this);
      }
    }
  }, {
    key: 'handleClick',
    value: function handleClick() {
      var theaterModeIsOn = document.getElementById(this.options_.elementToToggle).classList.toggle(this.options_.className);
      this.player().trigger('theaterMode', { 'theaterModeIsOn': theaterModeIsOn });

      if (theaterModeIsOn) {
        this.el_.classList.remove('vjs-theater-mode-control-open');
        this.el_.classList.add('vjs-theater-mode-control-close');
      } else {
        this.el_.classList.remove('vjs-theater-mode-control-close');
        this.el_.classList.add('vjs-theater-mode-control-open');
      }
    }
  }]);

  return TheaterModeToggle;
})(Button);

_videoJs2['default'].registerComponent('TheaterModeToggle', TheaterModeToggle);

var onPlayerReady = function onPlayerReady(player, options) {
  player.addClass('vjs-theater-mode');

  var toggle = player.controlBar.addChild(componentName, options);
  player.controlBar.el().insertBefore(toggle.el(), player.controlBar.fullscreenToggle.el());
};

/**
 * @function theaterMode
 * @param    {Object} [options={}]
 *           elementToToggle, the name of the DOM element to add/remove the 'theater-mode' CSS class
 */
var theaterMode = function theaterMode(options) {
  var _this = this;

  this.ready(function () {
    onPlayerReady(_this, _videoJs2['default'].mergeOptions(defaults, options));
  });

  this.on('fullscreenchange', function (event) {
    if (_this.isFullscreen()) {
      _this.controlBar.getChild(componentName).hide();
    } else {
      _this.controlBar.getChild(componentName).show();
    }
  });
};

// Register the plugin with video.js.
registerPlugin('theaterMode', theaterMode);

// Include the version number.
theaterMode.VERSION = _packageJson.version;

exports['default'] = theaterMode;
module.exports = exports['default'];

}).call(this,typeof global !== "undefined" ? global : typeof self !== "undefined" ? self : typeof window !== "undefined" ? window : {})
},{"../package.json":1}]},{},[2]);
