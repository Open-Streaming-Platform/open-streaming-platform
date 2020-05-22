var connection = null;
var fullJID = null;
var OccupantsArray = [];
var AvatarCache = {};
var userListActive = false;

// Start Connection on Load
$(window).bind('load', function() {
    var url = BOSH_SERVICE;
    connection = new Strophe.Connection(url);
    connection.rawInput = rawInput;
    connection.rawOutput = rawOutput;
    connection.connect(username + '@' + server, xmppPassword, onConnect);
});

// Disconnect XMPP on Page Unload
$(window).bind('unload', function(){
      // Leave Room First
      exitRoom(ROOMNAME + '@' + ROOM_SERVICE);
      // Execute XMPP Disconnection Process
      connection.options.sync = true; // Switch to using synchronous requests since this is typically called onUnload.
      connection.flush();
      connection.disconnect();
});

// Generate Profile Box on Username Click
$("#chatMembers a").click(function() {
  closeProfileBox();
  position = getPos($(this));
	var div = document.querySelector("div[data-type='profileBoxTemplate']").cloneNode(true);
	div.style.position = 'absolute';
	div.style.top =  position.y;///'10px';
	div.style.left = position.x;//'0px';
  div.style.zIndex = 10;
  div.style.display= "block";
  div.id="newProfileBox";
	$(this).after(div);
  })

// Hide Profile Box on Click Outside
$(document).mouseup(function(e)
{
  var container = $("#newProfileBox");
    if (!container.is(e.target) && container.has(e.target).length === 0)
    {
        container.remove();
    }
});

function showOccupants() {
    var chatOccupantsDiv = document.getElementById('chatMembers');
    var chatElementsDiv = document.getElementById('chat');

    if (userListActive == false) {
        chatOccupantsDiv.style.display = "block";
        chatElementsDiv.style.display = "none";
        userListActive = true;
    } else {
        chatOccupantsDiv.style.display = "none";
        chatElementsDiv.style.display = "block";
        userListActive = false;
        scrollChatWindow();
    }

}

function rawInput(data) {
  console.log('RECV: ' + data);
}

function rawOutput(data) {
  console.log('SENT: ' + data);
}

function log(msg) {
  $('#log').append('<div></div>').append(document.createTextNode(msg));
  console.log(msg);
}

// Function for Handling XMPP Connection, Joining a Room, and Initializing Intervals
function onConnect(status) {
  if (status == Strophe.Status.CONNECTING) {
    console.log('Connecting to XMPP Server...');
    document.getElementById('loader').style.display = "block";
    document.getElementById('chatPanel').style.display = "none";
  } else if (status == Strophe.Status.CONNFAIL) {
    console.log('Connection to XMPP Server Failed...');
    document.getElementById('loader').style.display = "none";
    document.getElementById('chatPanel').style.display = "none";
    $('#connect').get(0).value = 'connect';
  } else if (status == Strophe.Status.DISCONNECTING) {
    console.log('Disconnecting from XMPP Server...');
  } else if (status == Strophe.Status.DISCONNECTED) {
    console.log('Disconnected from XMPP Server...');
    document.getElementById('loader').style.display = "none";
    document.getElementById('chatPanel').style.display = "none";

    $('#connect').get(0).value = 'connect';
  } else if (status == Strophe.Status.CONNECTED) {
    console.log('Connected to XMPP Server.');
    fullJID = connection.jid; // full JID

    // set presence
    connection.send($pres());
    // set handlers
    connection.addHandler(onMessage, null, 'message', null, null, null);
    connection.addHandler(onSubscriptionRequest, null, "presence", "subscribe");
    connection.addHandler(onPresence, null, "presence");

    enterRoom(ROOMNAME + '@' + ROOM_SERVICE);
    setTimeout(function () {
        scrollChatWindow();
    }, 2000);
    document.getElementById('loader').style.display = "none";
    document.getElementById('chatPanel').style.display = "flex";
    queryOccupants();

    CHATSTATUS['jid'] = fullJID;
    var occupantCheck = setInterval(queryOccupants, 5000);
    var chatDataUpdate = setInterval(statusCheck, 5000);
    return true;
  }
}

function onSubscriptionRequest(stanza) {
  if (stanza.getAttribute("type") == "subscribe") {
    var from = $(stanza).attr('from');
    log('onSubscriptionRequest: from=' + from);
    // Send a 'subscribed' notification back to accept the incoming
    // subscription request
    connection.send($pres({
      to: from,
      type: "subscribed"
    }));
  }
  return true;
}

function onPresence(presence) {
  log('onPresence:');
  var presence_type = $(presence).attr('type'); // unavailable, subscribed, etc...
  var from = $(presence).attr('from'); // the jabber_id of the contact
  if (!presence_type) presence_type = "online";
  log(' >' + from + ' --> ' + presence_type);
  if (presence_type != 'error') {
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

function enterRoom(room) {
  console.log('Connecting to: ' + room);
  connection.muc.init(connection);
  connection.muc.join(room, username, room_msg_handler, room_pres_handler);
  connection.muc.setStatus(room, username + '@' + server, 'subscribed', 'chat');
  connection
  console.log('Connected to: ' + room);
  return true;
}

// Function for Sending Chat Input
function sendMessage() {
    var chatInput = document.getElementById('chatinput');
    var message = chatInput.value;
    if (message != '') {
        var o = {to: ROOMNAME + '@' + ROOM_SERVICE, type: 'groupchat'};
        var m = $msg(o);
        m.c('body', null, message);
        connection.send(m.tree());
        chatInput.value = "";
    }
    return true;
}


function room_msg_handler(a, b, c) {
  log('MUC: room_msg_handler');
  return true;
}

function room_pres_handler(a, b, c) {
  log('MUC: room_pres_handler');
  return true;
}

// Function to Handle New Messages
function onMessage(msg) {
  console.log(msg);
  var to = msg.getAttribute('to');
  var from = msg.getAttribute('from');
  var type = msg.getAttribute('type');
  var messageElement = msg.getElementsByTagName('body');
  var timestampElement = msg.getElementsByTagName('delay');
  if  (!(CHATSTATUS.muteList.includes(Strophe.getResourceFromJid(from)))) {

      if (timestampElement[0] != undefined) {
          var messageTimestamp = moment(timestampElement[0].getAttribute("stamp")).format('hh:mm A');
      } else {
          var messageTimestamp = moment().format('hh:mm A');
      }

      if (type == "chat" && messageElement.length > 0) {
          var body = messageElement[0];
          console.log('CHAT: I got a message from ' + from + ': ' + Strophe.getText(body));
      } else if (type == "groupchat" && messageElement.length > 0) {
          var body = messageElement[0];
          var room = Strophe.unescapeNode(Strophe.getNodeFromJid(from));
          // var nick = Strophe.getResourceFromJid(from);

          // nick = nick.replace('@' + server, '');

          var tempNode = document.querySelector("div[data-type='chatmessagetemplate']").cloneNode(true);
          tempNode.querySelector("div.chatTimestamp").textContent = messageTimestamp;
          tempNode.querySelector("div.chatUsername").textContent = Strophe.getResourceFromJid(from);
          tempNode.querySelector("div.chatMessage").textContent = Strophe.getText(body);
          tempNode.style.display = "block";
          chatDiv = document.getElementById("chat");
          var needsScroll = checkChatScroll()
          chatDiv.appendChild(tempNode);
          if (needsScroll) {
              scrollChatWindow();
          }
      }
  }

  return true;
}

// Handle Stick Chat Window Scroll
function checkChatScroll() {
  return (ChatContentWindow.scrollHeight - ChatContentWindow.offsetHeight) - ChatContentWindow.scrollTop <= 150;
}

function scrollChatWindow() {
  ChatContentWindow.scrollTop = ChatContentWindow.scrollHeight - ChatContentWindow.clientHeight;
}

// Retrieve Room Roster and Pass to Function to Parse Occupants
function queryOccupants() {
  var roomsData = connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE];
  parseOccupants(roomsData);
  return true;
}

// Update CHATSTATUS Variable with JID, Username, Role, & Affiliation
function statusCheck() {
  var roomsData = connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE];

  CHATSTATUS['username'] = roomsData.nick;
  var presumedUserObj = roomsData.roster[CHATSTATUS['username']];
  if (presumedUserObj.jid === CHATSTATUS['jid']) {
      CHATSTATUS['affiliation'] = presumedUserObj.affiliation;
      CHATSTATUS['role'] = presumedUserObj.role;
  }
  return true;
}

function parseOccupants(resp) {
  OccupantsArray = [];
  var elements = resp['roster'];

  // Parse Occupant Data and Store in Occupants Array
  for (user in elements) {
      var username = elements[user]['nick'];
      var affiliation = elements[user]['affiliation'];
      var role = elements[user]['role'];
      addUser(username, affiliation, role);
  }
  // Handle User Count
  var userCount = OccupantsArray.length;
  document.getElementById('chatTotal').innerHTML = userCount;

  var chatMembersArray = {moderator:[], participant:[], visitor:[], none:[]};
  for (let i = 0; i < OccupantsArray.length; i++) {
      chatMembersArray[OccupantsArray[i]['role']].push(OccupantsArray[i]);
  }
  // Update the chatMembers Div with listing of Members

  // Moderators
  document.getElementById('ModeratorList').innerHTML="";
  for (let i = 0; i < chatMembersArray['moderator'].length; i++) {
      var userEntry = document.createElement('div');
      userEntry.className = "member my-2";
      //userEntry.innerHTML = '<img class="rounded shadow" src="https://picsum.photos/48"> ' + '<span>' + chatMembersArray['owner'][i]['username'] + '</span>';
      userEntry.innerHTML = '<span class="user"><a href="javascript:void(0);">' + chatMembersArray['moderator'][i]['username'] + '</a></span>';
      document.getElementById('ModeratorList').appendChild(userEntry)
  }

  // Admins
  document.getElementById('ParticipantList').innerHTML="";
  for (let i = 0; i < chatMembersArray['participant'].length; i++) {
      var userEntry = document.createElement('div');
      userEntry.className = "member my-2";
      //userEntry.innerHTML = '<img class="rounded shadow" src="https://picsum.photos/48"> ' + '<span>' + chatMembersArray['participant'][i]['username'] + '</span>';
      userEntry.innerHTML = '<span class="user"><a href="javascript:void(0);">' + chatMembersArray['participant'][i]['username'] + '</a></span>';
      document.getElementById('ParticipantList').appendChild(userEntry)
  }

  // Visitor
  document.getElementById('VisitorList').innerHTML="";
  for (let i = 0; i < chatMembersArray['visitor'].length; i++) {
      //document.getElementById('chatMembers').append(chatMembersArray['none'][i]['username']);
      var userEntry = document.createElement('div');
      userEntry.className = "member my-2";
      //userEntry.innerHTML = '<img class="rounded shadow" src="https://picsum.photos/48"> ' + '<span>' + chatMembersArray['visitor'][i]['username'] + '</span>';
      userEntry.innerHTML = '<span class="user"><a href="javascript:void(0);">' + chatMembersArray['visitor'][i]['username'] + '</a></span>';
      document.getElementById('VisitorList').appendChild(userEntry)
  }

  return true;
}

function userExists(username) {
  return OccupantsArray.some(function(el) {
    return el.username === username;
  });
}

function addUser(username, affiliation, role) {
  if (userExists(username)) {
    return false;
  } else if (role == null) {
      return false;
  } else {
      OccupantsArray.push({ username: username, affiliation: affiliation, role: role });
  }

  return true;
}

function exitRoom(room) {
  console.log("Left Room: " + room);
  connection.muc.leave(room, username + '@' + server, null, null);
}

// Mod Controls
function ban(username) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].ban();
    return true;
}

function deop(username) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].deop();
    return true;
}

function kick(username) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].kick();
    return true;
}

function makeMember(username) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].member();
    return true;
}

function op(username) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].op();
    return true;
}

function revoke(username) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].revoke();
    return true;
}

function devoice(username) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].mute();
    return true;
}

function voice(username) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].voice();
    return true;
}

// User Controls
function mute(username) {
    CHATSTATUS.muteList.push(username);
    return true;
}

function unmute(username) {
    var index = CHATSTATUS.muteList.indexOf(username);
    if (index > -1) {
        CHATSTATUS.muteList.splice(index,1);
    }
    return true;
}


// Close Profile Box
function closeProfileBox() {
  var profileBox = document.getElementById('newProfileBox');
  if (profileBox != null) {
    document.getElementById('newProfileBox').remove();
  }
}

// Get Position to Generate Location for Profile Box
function getPos(el) {
    for (var lx=0, ly=0;
         el != null;
         lx += el.offsetLeft, ly += el.offsetTop, el = el.offsetParent);
    return {x: lx,y: ly};
}