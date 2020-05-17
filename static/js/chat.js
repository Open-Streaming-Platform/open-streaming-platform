var connection = null;
var fullJID = null;
var OccupantsArray = [];
var AvatarCache = {};
var userListActive = false;

var ChatContentWindow = document.getElementById("chatContentWindow");

$(window).bind('load', function() {
    var url = BOSH_SERVICE;
    connection = new Strophe.Connection(url);
    connection.rawInput = rawInput;
    connection.rawOutput = rawOutput;
    connection.connect(username + '@' + server, xmppPassword, onConnect);
});

$('#chatinput').on('keyup', function(e) {
      if (e.keyCode === 13) {
        sendMessage();
      }
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
    var occupantCheck = setInterval(queryOccupants, 5000);

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
  connection.muc.join(room, username + '@' + server, room_msg_handler, room_pres_handler);
  connection.muc.setStatus(room, username + '@' + server, 'subscribed', 'chat');
  connection
  console.log('Connected to: ' + room);
  return true;
}

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

function onMessage(msg) {
  console.log(msg);
  var to = msg.getAttribute('to');
  var from = msg.getAttribute('from');
  var type = msg.getAttribute('type');
  var messageElement = msg.getElementsByTagName('body');
  var timestampElement = msg.getElementsByTagName('delay');
  console.log(timestampElement);
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
      var nick = Strophe.getResourceFromJid(from);

      nick = nick.replace('@' + server, '');

      var tempNode = document.querySelector("div[data-type='chatmessagetemplate']").cloneNode(true);
      tempNode.querySelector("div.chatTimestamp").textContent = messageTimestamp;
      tempNode.querySelector("div.chatUsername").textContent = nick;
      tempNode.querySelector("div.chatMessage").textContent = Strophe.getText(body);
      tempNode.style.display = "block";
      chatDiv = document.getElementById("chat");
      var needsScroll = checkChatScroll()
      chatDiv.appendChild(tempNode);
      if (needsScroll) {
          scrollChatWindow();
      }
  }

  // we must return true to keep the handler alive.
  // returning false would remove it after it finishes.
  return true;
}

function checkChatScroll() {
  return (ChatContentWindow.scrollHeight - ChatContentWindow.offsetHeight) - ChatContentWindow.scrollTop <= 150;
}

function scrollChatWindow() {
  ChatContentWindow.scrollTop = ChatContentWindow.scrollHeight - ChatContentWindow.clientHeight;
}

function queryOccupants() {
  var roomsData = connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE];
  parseOccupants(roomsData);
}

function parseOccupants(resp) {
  OccupantsArray = [];
  var elements = resp['roster'];

  // Parse Occupant Data and Store in Occupants Array
  for (user in elements) {
      var jid = elements[user]['jid'];
      var username = elements[user]['nick'];
      var affiliation = elements[user]['affiliation'];
      var role = elements[user]['role'];
      addUser(jid, username, affiliation, role);
  }
  // Handle User Count
  var userCount = OccupantsArray.length;
  document.getElementById('chatTotal').innerHTML = userCount;

  var chatMembersArray = {owner:[], admin:[], member:[], none:[]};
  for (let i = 0; i < OccupantsArray.length; i++) {
      chatMembersArray[OccupantsArray[i]['affiliation']].push(OccupantsArray[i]);
  }
  // Update the chatMembers Div with listing of Members

  // Owners
  document.getElementById('OwnerList').innerHTML="";
  for (let i = 0; i < chatMembersArray['owner'].length; i++) {
      //document.getElementById('chatMembers').append(chatMembersArray['owner'][i]['username']);
      var userEntry = document.createElement('div');
      userEntry.className = "member my-2";
      userEntry.innerHTML = '<img class="rounded shadow" src="https://picsum.photos/48"> ' + '<span>' + chatMembersArray['owner'][i]['username'] + '</span>';
      document.getElementById('OwnerList').appendChild(userEntry)
  }

  // Admins
  document.getElementById('AdminList').innerHTML="";
  for (let i = 0; i < chatMembersArray['admin'].length; i++) {
      //document.getElementById('chatMembers').append(chatMembersArray['admin'][i]['username']);
      var userEntry = document.createElement('div');
      userEntry.className = "member my-2";
      userEntry.innerHTML = '<img class="rounded shadow" src="https://picsum.photos/48"> ' + '<span>' + chatMembersArray['admin'][i]['username'] + '</span>';
      document.getElementById('AdminList').appendChild(userEntry)
  }

  // Members
  document.getElementById('MemberList').innerHTML="";
  for (let i = 0; i < chatMembersArray['member'].length; i++) {
      //document.getElementById('chatMembers').append(chatMembersArray['member'][i]['username']);
      var userEntry = document.createElement('div');
      userEntry.className = "member my-2";
      userEntry.innerHTML = '<img class="rounded shadow" src="https://picsum.photos/48"> ' + '<span>' + chatMembersArray['member'][i]['username'] + '</span>';
      document.getElementById('MemberList').appendChild(userEntry)
  }

  // None
  document.getElementById('VisitorList').innerHTML="";
  for (let i = 0; i < chatMembersArray['none'].length; i++) {
      //document.getElementById('chatMembers').append(chatMembersArray['none'][i]['username']);
      var userEntry = document.createElement('div');
      userEntry.className = "member my-2";
      userEntry.innerHTML = '<img class="rounded shadow" src="https://picsum.photos/48"> ' + '<span>' + chatMembersArray['none'][i]['username'] + '</span>';
      document.getElementById('VisitorList').appendChild(userEntry)
  }

  return true;
}

function userExists(jid) {
  return OccupantsArray.some(function(el) {
    return el.jid === jid;
  });
}

function addUser(jid, username, affiliation, role) {
  if (userExists(jid)) {
    return false;
  }
  OccupantsArray.push({ jid: jid, username: username, affiliation: affiliation, role: role });
  return true;
}

function exitRoom(room) {
  console.log("Left Room: " + room);
  connection.muc.leave(room, username + '@' + server, null, null);
}