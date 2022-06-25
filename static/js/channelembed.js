// Chat Vars
var debug = false;
var connection = null;
var fullJID = null;
var OccupantsArray = [];
var AvatarCache = {};
var userListActive = false;
var modDisplayActive = false;

var occupantCheck;
var chatDataUpdate;

function rawInput(data) {
  console.log('RECV: ' + data);
}

function rawOutput(data) {
  console.log('SENT: ' + data);
}

function log(msg) {
  console.log(msg);
}

function connectChat() {
    document.getElementById('chat').innerHTML = "";
    var url = BOSH_SERVICE;
    connection = new Strophe.Connection(url);
    connection.rawInput = rawInput;
    connection.rawOutput = rawOutput;
    connection.connect(userUUID + '@' + server, xmppPassword, onConnect);
}

// Function for Handling XMPP Connection, Joining a Room, and Initializing Intervals
function onConnect(status) {
  if (status == Strophe.Status.CONNECTING) {
    console.log('Connecting to XMPP Server...');
  } else if (status == Strophe.Status.CONNFAIL) {
    console.log('Connection to XMPP Server Failed...');
  } else if (status == Strophe.Status.DISCONNECTING) {
    console.log('Disconnecting from XMPP Server...');
  } else if (status == Strophe.Status.DISCONNECTED) {
    console.log('Disconnected from XMPP Server...');
  } else if (status == Strophe.Status.CONNECTED) {
    console.log('Connected to XMPP Server.');
    fullJID = connection.jid; // full JID
    // set presence
    connection.send($pres());
    // set handlers
    connection.addHandler(onPresence, null, "presence");
    connection.disco.addFeature(Strophe.NS.PING);
    connection.ping.addPingHandler(onPing);

    enterRoom(ROOMNAME + '@' + ROOM_SERVICE);

    CHATSTATUS['jid'] = fullJID;

    return true;
  }
}

function onPresence(presence) {
    // disco stuff
    if (connection.disco) {
        connection.disco.info(fullJID)
        connection.disco.addIdentity('client', 'web', 'OSP Webchat', 'en');
    }
  var presence_type = $(presence).attr('type'); // unavailable, subscribed, etc...
  var from = $(presence).attr('from'); // the jabber_id of the contact
  if (!presence_type) presence_type = "online";
  log(' >' + from + ' --> ' + presence_type);
  if (presence_type !== 'error') {
    if (presence_type === 'unavailable') {
      // Mark contact as offline
    } else {
      var show = $(presence).find("show").text(); // this is what gives away, dnd, etc.
      if (show === 'chat' || show === '') {
        // Mark contact as online
      } else {
        // etc...
      }
    }
  }
  return true;
}

function onPing(ping) {
    connection.ping.pong(ping);
    return true;
}

function enterRoom(room) {
  console.log('Connecting to: ' + room);
  connection.muc.init(connection);
  if (CHANNELPROTECTED) {
      connection.muc.join(room, username, null, null, null, CHANNELTOKEN);
  } else {
      connection.muc.join(room, username, null, null, null);
  }
  connection.muc.setStatus(room, username + '@' + server, 'subscribed', 'chat');
  console.log('Connected to: ' + room);
  return true;
}

function exitRoom(room) {
  console.log("Left Room: " + room);
  connection.muc.leave(room, username + '@' + server, null, null);
}

// Begin Live Player Handler
//Fixes for VideoJS on Disconnect to Force a Reconnect when the readyState is stuck at 2 or when a live stream starts after having been offline
function monitor_vid(vidplayer){

    videoJSObj = vidplayer;
    currentReadyState = videoJSObj.readyState();

    videoContainer = document.getElementById('videoContainer');
    offlineWindow = document.getElementById('offlineImage');

    $.getJSON('/apiv1/channel/' + channelLocation + '/streams', function(data) {
        var streamList = data['results'];

        if (streamList.length > 0) {
            var currentStream = streamList[0];

            videoContainer.style.display = "block";
            offlineWindow.style.display = "none";

            if (currentReadyState <= 2) {
                try {
                    videoJSObj.reset();
                    videoJSObj.src(streamURL);
                    videoJSObj.pause();
                    videoJSObj.trigger('loadstart');
                    videoJSObj.play();
                } catch (e) {
                    console.log("OSP tried restarting the stream but had an issue:" + e)
                }
            }

        } else {
            try {
                videoJSObj.pause();
                videoJSObj.reset();
                videoContainer.style.display = "none";
                offlineWindow.style.display = "block";
            } catch(e) {
                console.log("OSP tried restarting the stream but had an issue:" + e)
            }
        }
    });
    var lastVideoState = currentReadyState;
}

// Execute the Video Monitor Script on Page Load
$(document).ready( function () {
    monitor_vid(player);
});

// Set the monitor video script to execute every 10s
setInterval(function() {
    monitor_vid(player);
}, 10000);
