/*! @name @antmedia/videojs-webrtc-plugin @version 2.0.0 @license MIT */
import videojs from 'video.js';
import _assertThisInitialized from '@babel/runtime/helpers/assertThisInitialized';
import _inheritsLoose from '@babel/runtime/helpers/inheritsLoose';

var COMMANDS = {
  TAKE_CANDIDATE: 'takeCandidate',
  TAKE_CONFIGURATION: 'takeConfiguration',
  PLAY: 'play',
  STOP: 'stop',
  GET_STREAM_INFO: 'getStreamInfo',
  PEER_MESSAGE_COMMAND: 'peerMessageCommand',
  FORCE_STREAM_QUALITY: 'forceStreamQuality',
  ERROR: 'error',
  NOTIFICATION: 'notification',
  STREAM_INFORMATION: 'streamInformation',
  PING: 'ping',
  PONG: 'pong',
  TRACK_LIST: 'trackList'
};

/**
 * WebSocketAdaptor for communication via webSocket
 */
var WebSocketAdaptor = /*#__PURE__*/function () {
  /**
   * Create a WebSocketAdaptor instance for communication via webSocket.
   *
   * @param  {Object} [initialValues]
   *         An initialValues object.
   *
   */
  function WebSocketAdaptor(initialValues) {
    for (var key in initialValues) {
      if (initialValues.hasOwnProperty(key)) {
        this[key] = initialValues[key];
      }
    }

    this.initWebSocketConnection();
  }
  /**
   * Initiate websocket connection.
   *
   * @param {function} callbackConnected callback if connected
   */


  var _proto = WebSocketAdaptor.prototype;

  _proto.initWebSocketConnection = function initWebSocketConnection(callbackConnected) {
    var _this = this;

    this.connecting = true;
    this.connected = false;
    this.pingTimerId = -1; // eslint-disable-next-line no-undef

    this.wsConn = new WebSocket(this.websocketUrl);

    this.wsConn.onopen = function () {
      _this.pingTimerId = setInterval(function () {
        _this.sendPing();
      }, 3000);
      _this.connected = true;
      _this.connecting = false;

      _this.callback('initialized');

      if (typeof callbackConnected !== 'undefined') {
        callbackConnected();
      }
    };

    this.wsConn.onmessage = function (event) {
      var obj = JSON.parse(event.data);

      switch (obj.command) {
        case COMMANDS.TAKE_CANDIDATE:
          {
            _this.webrtcadaptor.takeCandidate(obj.streamId, obj.label, obj.candidate);

            break;
          }

        case COMMANDS.TAKE_CONFIGURATION:
          {
            _this.webrtcadaptor.takeConfiguration(obj.streamId, obj.sdp, obj.type, obj.idMapping);

            break;
          }

        case COMMANDS.STOP:
          {
            _this.webrtcadaptor.closePeerConnection(obj.streamId);

            break;
          }

        case COMMANDS.ERROR:
          {
            _this.callbackError(obj.definition);

            break;
          }

        case COMMANDS.NOTIFICATION:
          {
            _this.callback(obj.definition, obj);

            if (obj.definition === 'play_finished' || obj.definition === 'publish_finished') {
              _this.webrtcadaptor.closePeerConnection(obj.streamId);
            }

            break;
          }

        case COMMANDS.STREAM_INFORMATION:
          {
            _this.callback(obj.command, obj);

            break;
          }

        case COMMANDS.PONG:
          {
            _this.callback(obj.command);

            break;
          }

        case COMMANDS.TRACK_LIST:
          {
            _this.callback(obj.command, obj);

            break;
          }

        case COMMANDS.PEER_MESSAGE_COMMAND:
          {
            _this.callback(obj.command, obj);

            break;
          }
      }
    };

    this.wsConn.onerror = function (error) {
      _this.connecting = false;
      _this.connected = false;

      _this.clearPingTimer();

      _this.callbackError('WebSocketNotConnected', error);
    };

    this.wsConn.onclose = function (event) {
      _this.connecting = false;
      _this.connected = false;

      _this.clearPingTimer();

      _this.callback('closed', event);
    };
  }
  /**
   * Clear websocket ping timer.
   */
  ;

  _proto.clearPingTimer = function clearPingTimer() {
    if (this.pingTimerId !== -1) {
      clearInterval(this.pingTimerId);
      this.pingTimerId = -1;
    }
  }
  /**
   * send Websocket ping message.
   */
  ;

  _proto.sendPing = function sendPing() {
    var jsCmd = {
      command: COMMANDS.PING
    };
    this.wsConn.send(JSON.stringify(jsCmd));
  }
  /**
   * close Websocket connection.
   */
  ;

  _proto.close = function close() {
    this.wsConn.close();
  }
  /**
   * send Websocket message method.
   *
   * @param {string} text message
   */
  ;

  _proto.send = function send(text) {
    var _this2 = this;

    if (!this.connecting && !this.connected) {
      // try to reconnect
      this.initWebSocketConnection(function () {
        _this2.send(text);
      });
      return;
    }

    this.wsConn.send(text);
  }
  /**
   * check Websocket connection.
   *
   * @return {boolean} status of websocket connection.
   */
  ;

  _proto.isConnected = function isConnected() {
    return this.connected;
  }
  /**
   * check Websocket connecting.
   *
   * @return {boolean} status of websocket connecting.
   */
  ;

  _proto.isConnecting = function isConnecting() {
    return this.connecting;
  };

  return WebSocketAdaptor;
}();

/**
 * Adaptor for WebRTC methods
 */

var WebRTCAdaptor = /*#__PURE__*/function () {
  /**
   * Create a WebRTCAdaptor instance.
   *
   * @param  {Object} initialValues
   *         A WebRTCAdaptor initial values.
   *
   */
  function WebRTCAdaptor(initialValues) {
    this.pcConfig = null;
    this.websocketUrl = null;
    this.sdpConstraints = null;
    this.remotePeerConnection = [];
    this.remoteDescriptionSet = [];
    this.iceCandidateList = [];
    this.playStreamId = [];
    this.player = null;
    this.webSocketAdaptor = null;
    this.viewerInfo = '';
    this.idMapping = [];
    this.candidateTypes = ['udp', 'tcp'];

    for (var key in initialValues) {
      if (initialValues.hasOwnProperty(key)) {
        this[key] = initialValues[key];
      }
    }

    this.remoteVideo = this.player;
    this.checkWebSocketConnection();
  }
  /**
   * play WebRTC stream.
   *
   * @param {string} streamId stream Id
   * @param {string} token stream token (opt)
   * @param {string} subscriberId subscriberId (opt)
   * @param {string} subscriberCode subscriberCode (opt)
   */


  var _proto = WebRTCAdaptor.prototype;

  _proto.play = function play(streamId, token, subscriberId, subscriberCode) {
    this.playStreamId.push(streamId);
    var jsCmd = {
      command: COMMANDS.PLAY,
      streamId: streamId,
      token: token,
      subscriberId: subscriberId ? subscriberId : '',
      subscriberCode: subscriberCode ? subscriberCode : '',
      viewerInfo: this.viewerInfo
    };
    this.webSocketAdaptor.send(JSON.stringify(jsCmd));
  }
  /**
   * stop playing WebRTC stream.
   *
   * @param {string} streamId stream Id
   */
  ;

  _proto.stop = function stop(streamId) {
    this.closePeerConnection(streamId);
    var jsCmd = {
      command: COMMANDS.STOP,
      streamId: streamId
    };
    this.webSocketAdaptor.send(JSON.stringify(jsCmd));
  }
  /**
   * get info about WebRTC stream.
   *
   * @param {string} streamId stream Id
   */
  ;

  _proto.getStreamInfo = function getStreamInfo(streamId) {
    var jsCmd = {
      command: COMMANDS.GET_STREAM_INFO,
      streamId: streamId
    };
    this.webSocketAdaptor.send(JSON.stringify(jsCmd));
  }
  /**
   * WebRTC onTrack event.
   *
   * @param {Object} event event object
   * @param {string} streamId stream Id
   */
  ;

  _proto.onTrack = function onTrack(event, streamId) {
    if (this.remoteVideo) {
      var vid = this.remoteVideo.tech().el();

      if (vid.srcObject !== event.streams[0]) {
        vid.srcObject = event.streams[0];
      }
    }
  }
  /**
   * Receive iceCandidate handler.
   *
   * @param {Object} event event object
   * @param {string} streamId stream Id
   */
  ;

  _proto.iceCandidateReceived = function iceCandidateReceived(event, streamId) {
    if (event.candidate) {
      var protocolSupported = false;

      if (event.candidate.candidate === '') {
        // event candidate can be received and its value can be "".
        // don't compare the protocols
        protocolSupported = true;
      } else if (typeof event.candidate.protocol === 'undefined') {
        this.candidateTypes.forEach(function (element) {
          if (event.candidate.candidate.toLowerCase().includes(element)) {
            protocolSupported = true;
          }
        });
      } else {
        protocolSupported = this.candidateTypes.includes(event.candidate.protocol.toLowerCase());
      }

      if (protocolSupported) {
        var jsCmd = {
          command: COMMANDS.TAKE_CANDIDATE,
          streamId: streamId,
          label: event.candidate.sdpMLineIndex,
          id: event.candidate.sdpMid,
          candidate: event.candidate.candidate
        };
        this.webSocketAdaptor.send(JSON.stringify(jsCmd));
      } else if (event.candidate.candidate !== '') {
        this.callbackError('protocol_not_supported', 'Support protocols: ' + this.candidateTypes.toString() + ' candidate: ' + event.candidate.candidate);
      }
    }
  }
  /**
   * Initiate WebRtc PeerConnection.
   *
   * @param {string} streamId stream Id
   */
  ;

  _proto.initPeerConnection = function initPeerConnection(streamId) {
    var _this = this;

    if (!this.remotePeerConnection[streamId]) {
      var closedStreamId = streamId; // eslint-disable-next-line no-undef

      this.remotePeerConnection[streamId] = new RTCPeerConnection(this.pcConfig);
      this.remoteDescriptionSet[streamId] = false;
      this.iceCandidateList[streamId] = [];

      this.remotePeerConnection[streamId].onicecandidate = function (event) {
        _this.iceCandidateReceived(event, closedStreamId);
      };

      this.remotePeerConnection[streamId].ontrack = function (event) {
        _this.onTrack(event, closedStreamId);
      };

      this.remotePeerConnection[streamId].oniceconnectionstatechange = function () {
        var obj = {
          state: _this.remotePeerConnection[streamId].iceConnectionState,
          streamId: streamId
        };

        _this.callback('ice_connection_state_changed', obj);
      };
    }
  }
  /**
   * Close WebRtc PeerConnection.
   *
   * @param {string} streamId stream Id
   */
  ;

  _proto.closePeerConnection = function closePeerConnection(streamId) {
    if (this.remotePeerConnection[streamId]) {
      if (this.remotePeerConnection[streamId].signalingState !== 'closed') {
        this.remotePeerConnection[streamId].close();
        this.remotePeerConnection[streamId] = null;
        delete this.remotePeerConnection[streamId];
        this.playStreamId = this.playStreamId.filter(function (item) {
          return item !== streamId;
        });
      }
    }
  }
  /**
   * Got the SDP.
   *
   * @param {RTCSessionDescriptionInit} configuration sdp
   * @param {string} streamId stream Id
   */
  ;

  _proto.gotDescription = function gotDescription(configuration, streamId) {
    var _this2 = this;

    this.remotePeerConnection[streamId].setLocalDescription(configuration).then(function () {
      var jsCmd = {
        command: COMMANDS.TAKE_CONFIGURATION,
        streamId: streamId,
        type: configuration.type,
        sdp: configuration.sdp
      };

      _this2.webSocketAdaptor.send(JSON.stringify(jsCmd));
    });
  }
  /**
   * take the SDP.
   *
   * @param {string} idOfStream id of stream
   * @param {RTCSessionDescriptionInit} configuration sdp
   * @param {string} typeOfConfiguration stream Id
   * @param {Object} idMapping track Ids
   */
  ;

  _proto.takeConfiguration = function takeConfiguration(idOfStream, configuration, typeOfConfiguration, idMapping) {
    var _this3 = this;

    var streamId = idOfStream;
    this.idMapping[streamId] = idMapping;
    this.initPeerConnection(streamId); // eslint-disable-next-line no-undef

    this.remotePeerConnection[streamId].setRemoteDescription({
      sdp: configuration,
      type: typeOfConfiguration
    }).then(function () {
      _this3.remoteDescriptionSet[streamId] = true;
      var length = _this3.iceCandidateList[streamId].length;

      for (var i = 0; i < length; i++) {
        _this3.addIceCandidate(streamId, _this3.iceCandidateList[streamId][i]);
      }

      _this3.iceCandidateList[streamId] = [];

      if (typeOfConfiguration === 'offer') {
        _this3.remotePeerConnection[streamId].createAnswer(_this3.sdpConstraints).then(function (config) {
          // support for stereo
          config.sdp = config.sdp.replace('useinbandfec=1', 'useinbandfec=1; stereo=1');

          _this3.gotDescription(config, streamId);
        });
      }
    }).catch(function (error) {
      if (error.toString().includes('InvalidAccessError') || error.toString().includes('setRemoteDescription')) {
        /**
         * This error generally occurs in codec incompatibility.
         * AMS for a now supports H.264 codec. This error happens when some browsers try to open it from VP8.
         */
        _this3.callbackError('notSetRemoteDescription');
      }
    });
  }
  /**
   * take the Ice Candidate.
   *
   * @param {string} idOfTheStream id of stream
   * @param {string} label sdpMLineIndex
   * @param {Object} takingCandidate candidate
   */
  ;

  _proto.takeCandidate = function takeCandidate(idOfTheStream, label, takingCandidate) {
    var streamId = idOfTheStream; // eslint-disable-next-line no-undef

    var candidate = new RTCIceCandidate({
      sdpMLineIndex: label,
      candidate: takingCandidate
    });
    this.initPeerConnection(streamId);

    if (this.remoteDescriptionSet[streamId] === true) {
      this.addIceCandidate(streamId, candidate);
    } else {
      this.iceCandidateList[streamId].push(candidate);
    }
  }
  /**
   * take the Ice Candidate.
   *
   * @param {string} streamId id of stream
   * @param {Object} candidate candidate
   */
  ;

  _proto.addIceCandidate = function addIceCandidate(streamId, candidate) {
    var protocolSupported = false;

    if (candidate.candidate === '') {
      protocolSupported = true;
    } else if (typeof candidate.protocol === 'undefined') {
      this.candidateTypes.forEach(function (element) {
        if (candidate.candidate.toLowerCase().includes(element)) {
          protocolSupported = true;
        }
      });
    } else {
      protocolSupported = this.candidateTypes.includes(candidate.protocol.toLowerCase());
    }

    if (protocolSupported) {
      this.remotePeerConnection[streamId].addIceCandidate(candidate);
    }
  }
  /**
   * closing WebSocket connection.
   */
  ;

  _proto.closeWebSocket = function closeWebSocket() {
    for (var key in this.remotePeerConnection) {
      this.remotePeerConnection[key].close();
    } // free the remote peer connection by initializing again


    this.remotePeerConnection = [];
    this.webSocketAdaptor.close();
  }
  /**
   * check WebSocket connection.
   */
  ;

  _proto.checkWebSocketConnection = function checkWebSocketConnection() {
    var isWebSocketAvailable = this.webSocketAdaptor;
    var isWebSocketConnected = isWebSocketAvailable && this.webSocketAdaptor.isConnected() && this.webSocketAdaptor.isConnecting();

    if (!isWebSocketAvailable || !isWebSocketConnected) {
      try {
        this.webSocketAdaptor = new WebSocketAdaptor({
          websocketUrl: this.websocketUrl,
          webrtcadaptor: this,
          callback: this.callback,
          callbackError: this.callbackError
        });
      } catch (e) {
        this.player.createModal('WebSocket connect error');
      }
    }
  }
  /**
   * send peer message
   *
   * @param {string} streamId id of stream
   * @param {string} definition message definition
   * @param {string} data message data
   */
  ;

  _proto.peerMessage = function peerMessage(streamId, definition, data) {
    var jsCmd = {
      command: COMMANDS.PEER_MESSAGE_COMMAND,
      streamId: streamId,
      definition: definition,
      data: data
    };
    this.webSocketAdaptor.send(JSON.stringify(jsCmd));
  }
  /**
   * force stream quality
   *
   * @param {string} streamId id of stream
   * @param {string} resolution stream resolution
   */
  ;

  _proto.forceStreamQuality = function forceStreamQuality(streamId, resolution) {
    var jsCmd = {
      command: COMMANDS.FORCE_STREAM_QUALITY,
      streamId: streamId,
      streamHeight: resolution
    };
    this.webSocketAdaptor.send(JSON.stringify(jsCmd));
  };

  return WebRTCAdaptor;
}();

var ANT_CALLBACKS = {
  INITIALIZED: 'initialized',
  PLAY_STARTED: 'play_started',
  PLAY_FINISHED: 'play_finished',
  CLOSED: 'closed',
  STREAM_INFORMATION: 'streamInformation',
  RESOLUTION_CHANGE_INFO: 'resolutionChangeInfo'
};

var MenuItem = videojs.getComponent('MenuItem');
var Component = videojs.getComponent('Component');

var ResolutionMenuItem = /*#__PURE__*/function (_MenuItem) {
  _inheritsLoose(ResolutionMenuItem, _MenuItem);

  function ResolutionMenuItem(player, options) {
    options.selectable = true;
    options.multiSelectable = false;
    return _MenuItem.call(this, player, options) || this;
  }

  var _proto = ResolutionMenuItem.prototype;

  _proto.handleClick = function handleClick() {
    this.options().plugin.changeStreamQuality(this.options().value);
  };

  return ResolutionMenuItem;
}(MenuItem);

Component.registerComponent('ResolutionMenuItem', ResolutionMenuItem);

var MenuButton = videojs.getComponent('MenuButton');

var ResolutionMenuButton = /*#__PURE__*/function (_MenuButton) {
  _inheritsLoose(ResolutionMenuButton, _MenuButton);

  function ResolutionMenuButton(player, options) {
    var _this;

    _this = _MenuButton.call(this, player, options) || this;
    MenuButton.apply(_assertThisInitialized(_this), arguments);
    return _this;
  }

  var _proto = ResolutionMenuButton.prototype;

  _proto.createEl = function createEl() {
    return videojs.dom.createEl('div', {
      className: 'vjs-http-source-selector vjs-menu-button vjs-menu-button-popup vjs-control vjs-button'
    });
  };

  _proto.buildCSSClass = function buildCSSClass() {
    return MenuButton.prototype.buildCSSClass.call(this) + ' vjs-icon-cog';
  };

  _proto.update = function update() {
    return MenuButton.prototype.update.call(this);
  };

  _proto.createItems = function createItems() {
    var menuItems = [];
    var levels = [{
      label: 'auto',
      value: 0
    }].concat(this.player().resolutions);

    for (var i = 0; i < levels.length; i++) {
      menuItems.push(new ResolutionMenuItem(this.player_, {
        label: levels[i].label,
        value: levels[i].value,
        selected: levels[i].value === this.player().selectedResolution,
        plugin: this.options().plugin,
        streamName: this.options().streamName
      }));
    }

    return menuItems;
  };

  return ResolutionMenuButton;
}(MenuButton);

var defaults = {
  sdpConstraints: {
    OfferToReceiveAudio: true,
    OfferToReceiveVideo: true
  },
  mediaConstraints: {
    video: false,
    audio: false
  }
};
/**
 * An advanced Video.js plugin for playing WebRTC stream from Ant-mediaserver
 */

var WebRTCHandler = /*#__PURE__*/function () {
  /**
   * Create a WebRTC source handler instance.
   *
   * @param  {Object} source
   *         Source object that is given in the DOM, includes the stream URL
   *
   * @param  {Object} [options]
   *         Options include:
   *            ICE Server
   *            Tokens
   *            Subscriber ID
   *            Subscriber code
   */
  function WebRTCHandler(source, tech, options) {
    var _this = this;

    this.player = videojs(options.playerId);
    this.initiateWebRTCAdaptor(source, options);
    this.player.ready(function () {
      _this.player.addClass('videojs-webrtc-plugin');
    });
    this.player.on('playing', function () {
      if (_this.player.el().getElementsByClassName('vjs-custom-spinner').length) {
        _this.player.el().removeChild(_this.player.spinner);
      }
    });
    videojs.registerComponent('ResolutionMenuButton', ResolutionMenuButton);
    videojs.registerComponent('ResolutionMenuItem', ResolutionMenuItem);
  }
  /**
   * Initiate WebRTCAdaptor.
   *
   * @param  {Object} [options]
   * An optional options object.
   *
   */


  var _proto = WebRTCHandler.prototype;

  _proto.initiateWebRTCAdaptor = function initiateWebRTCAdaptor(source, options) {
    var _this2 = this;

    this.options = videojs.mergeOptions(defaults, options);
    this.source = source;
    this.source.pcConfig = {
      iceServers: JSON.parse(source.iceservers)
    };
    this.source.mediaServerUrl = source.src.split('/').slice(0, 4).join('/') + "/websocket";
    this.source.streamName = source.src.split('/')[4].split('.webrtc')[0];
    this.source.token = this.getUrlParameter('token');
    this.source.subscriberId = this.getUrlParameter('subscriberId');
    this.source.subscriberCode = this.getUrlParameter('subscriberCode');
    this.webRTCAdaptor = new WebRTCAdaptor({
      websocketUrl: this.source.mediaServerUrl,
      mediaConstraints: this.source.mediaConstraints,
      pcConfig: this.source.pcConfig,
      sdpConstraints: this.source.sdpConstraints,
      player: this.player,
      callback: function callback(info, obj) {
        switch (info) {
          case ANT_CALLBACKS.INITIALIZED:
            {
              _this2.initializedHandler();

              break;
            }

          case ANT_CALLBACKS.PLAY_STARTED:
            {
              _this2.joinStreamHandler(obj);

              break;
            }

          case ANT_CALLBACKS.PLAY_FINISHED:
            {
              _this2.leaveStreamHandler(obj);

              break;
            }

          case ANT_CALLBACKS.STREAM_INFORMATION:
            {
              _this2.streamInformationHandler(obj);

              break;
            }

          case ANT_CALLBACKS.RESOLUTION_CHANGE_INFO:
            {
              _this2.resolutionChangeHandler(obj);

              break;
            }

          default:
            {
              _this2.defaultHandler(info);

              break;
            }
        }
      },
      callbackError: function callbackError(error) {
        // add error handler
        // some of the possible errors, NotFoundError, SecurityError,PermissionDeniedError
        var ModalDialog = videojs.getComponent('ModalDialog');

        if (_this2.errorModal) {
          _this2.errorModal.close();
        }

        _this2.errorModal = new ModalDialog(_this2.player, {
          content: "ERROR: " + JSON.stringify(error),
          temporary: true,
          pauseOnOpen: false,
          uncloseable: true
        });

        _this2.player.addChild(_this2.errorModal);

        _this2.errorModal.open();

        _this2.errorModal.setTimeout(function () {
          return _this2.errorModal.close();
        }, 3000);

        _this2.player.trigger('webrtc-error', {
          error: error
        });
      }
    });
  }
  /**
   * after websocket success connection.
   */
  ;

  _proto.initializedHandler = function initializedHandler() {
    this.webRTCAdaptor.play(this.source.streamName, this.source.token, this.source.subscriberId, this.source.subscriberCode);
  }
  /**
   * after joined stream handler
   *
   * @param {Object} obj callback artefacts
   */
  ;

  _proto.joinStreamHandler = function joinStreamHandler(obj) {
    this.webRTCAdaptor.getStreamInfo(this.source.streamName);
  }
  /**
   * after left stream.
   */
  ;

  _proto.leaveStreamHandler = function leaveStreamHandler() {
    // reset stream resolutions in dropdown
    this.player.resolutions = [];
    this.player.controlBar.getChild('ResolutionMenuButton').update();
  }
  /**
   * stream information handler.
   *
   * @param {Object} obj callback artefacts
   */
  ;

  _proto.streamInformationHandler = function streamInformationHandler(obj) {
    var streamResolutions = obj.streamInfo.reduce(function (unique, item) {
      return unique.includes(item.streamHeight) ? unique : [].concat(unique, [item.streamHeight]);
    }, []).sort(function (a, b) {
      return b - a;
    });
    this.player.resolutions = streamResolutions.map(function (resolution) {
      return {
        label: resolution,
        value: resolution
      };
    });
    this.player.selectedResolution = 0;
    this.addResolutionButton();
  };

  _proto.addResolutionButton = function addResolutionButton() {
    var controlBar = this.player.controlBar;
    var fullscreenToggle = controlBar.getChild('fullscreenToggle').el();

    if (controlBar.getChild('ResolutionMenuButton')) {
      controlBar.removeChild('ResolutionMenuButton');
    }

    controlBar.el().insertBefore(controlBar.addChild('ResolutionMenuButton', {
      plugin: this,
      streamName: this.source.streamName
    }).el(), fullscreenToggle);
  }
  /**
   * change resolution handler.
   *
   * @param {Object} obj callback artefacts
   */
  ;

  _proto.resolutionChangeHandler = function resolutionChangeHandler(obj) {
    var _this3 = this;

    // eslint-disable-next-line no-undef
    this.player.spinner = document.createElement('div');
    this.player.spinner.className = 'vjs-custom-spinner';
    this.player.el().appendChild(this.player.spinner);
    this.player.pause();
    this.player.setTimeout(function () {
      if (_this3.player.el().getElementsByClassName('vjs-custom-spinner').length) {
        _this3.player.el().removeChild(_this3.player.spinner);

        _this3.player.play();
      }
    }, 2000);
  }
  /**
   * default handler.
   *
   * @param {string} info callback event info
   */
  ;

  _proto.defaultHandler = function defaultHandler(info) {// eslint-disable-next-line no-console
    // console.log(info + ' notification received');
  };

  _proto.changeStreamQuality = function changeStreamQuality(value) {
    this.webRTCAdaptor.forceStreamQuality(this.source.streamName, value);
    this.player.selectedResolution = value;
    this.player.controlBar.getChild('ResolutionMenuButton').update();
  }
  /**
   * get url parameter
   *
   * @param {string} param callback event info
   */
  ;

  _proto.getUrlParameter = function getUrlParameter(param) {
    if (this.source.src.includes('?')) {
      var urlParams = this.source.src.split('?')[1].split('&').reduce(function (p, e) {
        var a = e.split('=');
        p[decodeURIComponent(a[0])] = decodeURIComponent(a[1]);
        return p;
      }, {}) || {};
      return urlParams[param];
    }

    return null;
  };

  return WebRTCHandler;
}();

var webRTCSourceHandler = {
  name: 'videojs-webrtc-plugin',
  VERSION: '1.1',
  canHandleSource: function canHandleSource(srcObj, options) {
    if (options === void 0) {
      options = {};
    }

    var localOptions = videojs.mergeOptions(videojs.options, options);
    localOptions.source = srcObj.src;
    return webRTCSourceHandler.canPlayType(srcObj.type, localOptions);
  },
  handleSource: function handleSource(source, tech, options) {
    if (options === void 0) {
      options = {};
    }

    var localOptions = videojs.mergeOptions(videojs.options, options); // Register the plugin to source handler tech

    tech.webrtc = new WebRTCHandler(source, tech, localOptions);
    return tech.webrtc;
  },
  canPlayType: function canPlayType(type, options) {
    if (options === void 0) {
      options = {};
    }

    var mediaUrl = options.source;

    if (mediaUrl.split('/')[4].includes('.webrtc')) {
      return 'maybe';
    }

    return '';
  }
}; // register source handlers with the appropriate techs

videojs.getTech('Html5').registerSourceHandler(webRTCSourceHandler, 0);
var plugin = {
  WebRTCHandler: WebRTCHandler,
  webRTCSourceHandler: webRTCSourceHandler
};

export default plugin;
