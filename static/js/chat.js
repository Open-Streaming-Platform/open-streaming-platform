var debug = false;
var connection = null;
var fullJID = null;
var OccupantsArray = [];
var AvatarCache = {};
var userListActive = false;
var banListActive = false;

var occupantCheck;
var chatDataUpdate;

function showOccupants() {
    var chatOccupantsDiv = document.getElementById('chatMembers');
    var chatElementsDiv = document.getElementById('chat');
    var banList = document.getElementById('bannedUsers');

    if (userListActive == false) {
        banList.style.display = "none";
        chatOccupantsDiv.style.display = "block";
        chatElementsDiv.style.display = "none";
        banListActive = false;
        userListActive = true;
    } else {
        banList.style.display = "none";
        chatOccupantsDiv.style.display = "none";
        chatElementsDiv.style.display = "block";
        userListActive = false;
        scrollChatWindow();
    }
}

function openBanList() {
    var chatOccupantsDiv = document.getElementById('chatMembers');
    var chatElementsDiv = document.getElementById('chat');
    var banList = document.getElementById('bannedUsers');

    if (banListActive == false) {
        getBanList();
        banList.style.display = "block";
        chatOccupantsDiv.style.display = "none";
        chatElementsDiv.style.display = "none";
        userListActive = false;
        banListActive = true;
    } else {
        banList.style.display = "none";
        chatOccupantsDiv.style.display = "none";
        chatElementsDiv.style.display = "block";
        banListActive = false;
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

function connectChat() {
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
    document.getElementById('bannedUsers').style.display = 'none';
    document.getElementById('unavailable').style.display = "none";
    document.getElementById('loader').style.display = "block";
    document.getElementById('chatPanel').style.display = "none";
  } else if (status == Strophe.Status.CONNFAIL) {
    console.log('Connection to XMPP Server Failed...');
    document.getElementById('bannedUsers').style.display = 'none';
    document.getElementById('unavailable').style.display = "block";
    document.getElementById('loader').style.display = "none";
    document.getElementById('chatPanel').style.display = "none";
    $('#connect').get(0).value = 'connect';
  } else if (status == Strophe.Status.DISCONNECTING) {
    console.log('Disconnecting from XMPP Server...');
  } else if (status == Strophe.Status.DISCONNECTED) {
    console.log('Disconnected from XMPP Server...');
    document.getElementById('bannedUsers').style.display = 'none';
    document.getElementById('chatPanel').style.display = "none";
    document.getElementById('loader').style.display = "none";
    document.getElementById('unavailable').style.display = "block";

    document.getElementById('reasonCode').textContent = "999";
    document.getElementById('reasonText').textContent = "Disconnected.";
  } else if (status == Strophe.Status.CONNECTED) {
    console.log('Connected to XMPP Server.');
    fullJID = connection.jid; // full JID
    // set presence
    connection.send($pres());
    // set handlers
    connection.addHandler(onMessage, null, 'message', null, null, null);
    connection.addHandler(onSubscriptionRequest, null, "presence", "subscribe");
    connection.addHandler(onPresence, null, "presence");
    connection.disco.addFeature(Strophe.NS.PING);
    connection.ping.addPingHandler(onPing);

    enterRoom(ROOMNAME + '@' + ROOM_SERVICE);
    setTimeout(function () {
        scrollChatWindow();
    }, 2000);
    document.getElementById('loader').style.display = "none";
    document.getElementById('chatPanel').style.display = "flex";
    queryOccupants();

    CHATSTATUS['jid'] = fullJID;
    occupantCheck = setInterval(queryOccupants, 5000);
    chatDataUpdate = setInterval(statusCheck, 5000);
    return true;
  }
}

function onPing(ping) {
    connection.ping.pong(ping);
    return true;
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
    // disco stuff
    if (connection.disco) {
        connection.disco.info(fullJID)
        connection.disco.addIdentity('client', 'web', 'OSP Webchat', 'en');
    }
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
  if (CHANNELPROTECTED) {
      connection.muc.join(room, username, room_msg_handler, room_pres_handler, room_roster_handler, CHANNELTOKEN);
  } else {
      connection.muc.join(room, username, room_msg_handler, room_pres_handler, room_roster_handler);
  }
  connection.muc.setStatus(room, username + '@' + server, 'subscribed', 'chat');
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
    if (debug == true) {
        console.log(a);
        console.log(b);
        console.log(c);
    }
  //log('MUC: room_msg_handler');
  return true;
}

function room_pres_handler(a, b, c) {
  if (debug == true) {
      console.log(a);
      console.log(b);
      console.log(c);
  }
  var presenceStatement = a;
  var from = presenceStatement.attributes.from.value;
  var to = presenceStatement.attributes.to.value;
  var status = [];
  var statusNodes = $(presenceStatement).find("status");
  for (let i = 0; i < statusNodes.length; i++) {
      var statuscode = statusNodes[i].attributes.code.value;
      status.push(statuscode);
  }

  if (presenceStatement.attributes.type !== undefined && presenceStatement.attributes.type !== null) {
    var presenceType = presenceStatement.attributes.type.value;
  } else {
    var presenceType = 'online';
  }

  // Handle Public Presence Notifications
  var messageTimestamp = moment().format('hh:mm A');
  if (presenceType == "unavailable") {

      var msgfrom = "SERVER";
      if (status.includes("307")) {
          msg = Strophe.getResourceFromJid(from) + " was kicked from the room.";
      } else if (status.includes("301")) {
          msg = Strophe.getResourceFromJid(from) + " was banned from the room.";
      } else {
          msg = Strophe.getResourceFromJid(from) + " has left the room.";
      }
      serverMessage(msg);
  //} else if (presenceType == 'online') {
  //    msg = Strophe.getResourceFromJid(from) + " joined the room.";
  //    serverMessage(msg);
  }

  // Check if is own status change (Kicks/Bans/Etc)
  if (from === ROOMNAME + '@' + ROOM_SERVICE + '/' + username && to === fullJID) {
      console.log("Current User Status Change to: " + presenceType)
      if (presenceType == "unavailable") {

          clearInterval(occupantCheck);
          clearInterval(chatDataUpdate);

          document.getElementById('bannedUsers').style.display = 'none';
          document.getElementById('chatPanel').style.display = "none";
          document.getElementById('loader').style.display = "none";
          document.getElementById('unavailable').style.display = "block";

          reasonCodeSpan = document.getElementById('reasonCode');
          reasonTextSpan = document.getElementById('reasonText');

          if (status.includes("307")) {
              reasonCodeSpan.textContent = "307";
              reasonTextSpan.textContent = "You have been kicked from the room.";
          } else if (status.includes("301")) {
              reasonCodeSpan.textContent = "301";
              reasonTextSpan.textContent = "You have been banned from the room.";
          } else if (status.includes("321")) {
              reasonCodeSpan.textContent = "321";
              reasonTextSpan.textContent = "You have been removed from the room due to an affiliation change.";
          } else if (status.includes("322")) {
              reasonCodeSpan.textContent = "322";
              reasonTextSpan.textContent = "You have been removed from the room because it has been changed to members-only.";
          } else if (status.includes("332")) {
              reasonCodeSpan.textContent = "332";
              reasonTextSpan.textContent = "You have been removed from the room because of a system shutdown.";
          } else {
              reasonCodeSpan.textContent = "999";
              reasonTextSpan.textContent = "Disconnection";
          }
      } else if (presenceType == "error") {
          error = $(presenceStatement).find("error");
          errorCode = error[0].attributes.code.value;
          clearInterval(occupantCheck);
          clearInterval(chatDataUpdate);
          document.getElementById('bannedUsers').style.display = 'none';
          document.getElementById('chatPanel').style.display = "none";
          document.getElementById('loader').style.display = "none";
          document.getElementById('unavailable').style.display = "block";
          reasonCodeSpan.textContent = errorCode;
          if (errorCode === "403") {
              reasonTextSpan.textContent = "Unauthorized to join room"
          }
      }
  }
  return true;
}

function room_roster_handler(a,b,c) {
    if (debug == true) {
        console.log(a);
        console.log(b);
        console.log(c);
    }
}

// Function for Showing Messages as Server to Client
function serverMessage(msg) {
    var msgfrom = "SERVER";
    var messageTimestamp = moment().format('hh:mm A');

    var tempNode = document.querySelector("div[data-type='chatmessagetemplate']").cloneNode(true);
    tempNode.querySelector("span.chatTimestamp").textContent = messageTimestamp;
    tempNode.querySelector("span.chatUsername").innerHTML = '<span class="user">' + msgfrom + '</span>';
    tempNode.querySelector("span.chatMessage").innerHTML = format_msg(msg);
    tempNode.style.display = "block";
    chatDiv = document.getElementById("chat");
    var needsScroll = checkChatScroll()
    chatDiv.appendChild(tempNode);
    if (needsScroll) {
        scrollChatWindow();
    }
}

// Function to Handle New Messages
function onMessage(msg) {
  var to = msg.getAttribute('to');
  var from = msg.getAttribute('from');
  var type = msg.getAttribute('type');
  var messageElement = msg.getElementsByTagName('body');
  var timestampElement = msg.getElementsByTagName('delay');

  if (Strophe.getResourceFromJid(from) == null) {
      from = ROOMNAME + "@" + ROOM_SERVICE + "/SERVER";
  }

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
          var msg = Strophe.xmlunescape(Strophe.getText(body))

          var tempNode = document.querySelector("div[data-type='chatmessagetemplate']").cloneNode(true);
          tempNode.querySelector("span.chatTimestamp").textContent = messageTimestamp;
          if (Strophe.getResourceFromJid(from) == 'SERVER') {
              tempNode.querySelector("span.chatUsername").innerHTML = '<span class="user">' + Strophe.getResourceFromJid(from) + '</span>';
          } else {
              tempNode.querySelector("span.chatUsername").innerHTML = '<span class="user"><a href="javascript:void(0);" onclick="displayProfileBox(this)">' + Strophe.getResourceFromJid(from) + '</a></span>';
          }
          tempNode.querySelector("span.chatMessage").innerHTML = format_msg(msg);
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

// format message
function format_msg(msg){
    msg = msg.replace(/<\/?[^>]+(>|$)/g, '');
    msg = msg.replace(/(?:\r\n|\r|\n)/g, '<br>');
    return msg
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
  if (presumedUserObj != undefined) {
      if (presumedUserObj.jid === CHATSTATUS['jid']) {
          CHATSTATUS['affiliation'] = presumedUserObj.affiliation;
          CHATSTATUS['role'] = presumedUserObj.role;
      }
  } else {
      CHATSTATUS['affiliation'] = "none";
      CHATSTATUS['role'] = "none";
  }

  // Update UI based on Roles
  if (CHATSTATUS['role'] === "moderator") {
      document.getElementById('banListButton').style.display = "inline";
  } else {
      document.getElementById('banListButton').style.display = "none";
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
      userEntry.className = "member my-1";
      userEntry.innerHTML = '<span class="user"><a href="javascript:void(0);" onclick="displayProfileBox(this)">' + chatMembersArray['moderator'][i]['username'] + '</a></span>';
      document.getElementById('ModeratorList').appendChild(userEntry)
  }

  // Admins
  document.getElementById('ParticipantList').innerHTML="";
  for (let i = 0; i < chatMembersArray['participant'].length; i++) {
      var userEntry = document.createElement('div');
      userEntry.className = "member my-1";
      userEntry.innerHTML = '<span class="user"><a href="javascript:void(0);" onclick="displayProfileBox(this)">' + chatMembersArray['participant'][i]['username'] + '</a></span>';
      document.getElementById('ParticipantList').appendChild(userEntry)
  }

  // Visitor
  document.getElementById('VisitorList').innerHTML="";
  for (let i = 0; i < chatMembersArray['visitor'].length; i++) {
      var userEntry = document.createElement('div');
      userEntry.className = "member my-1";
      userEntry.innerHTML = '<span class="user"><a href="javascript:void(0);" onclick="displayProfileBox(this)">' + chatMembersArray['visitor'][i]['username'] + '</a></span>';
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

function hideUserMessages(nickname) {
    var msgDivs = $("div > .chatUsername:contains('" + nickname + "')");
    msgDivs.parent().parent().parent().parent().hide();
    return true;
}

// Mod Controls
function ban(username) {
    var userUUID = connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username]['jid'].split('@')[0]
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].ban();
    socket.emit('banUser', {channelLoc: ROOMNAME, banUsername: username, banUserUUID: userUUID});
    return true;
}

function unban(uuid) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].modifyAffiliation(uuid + '@' + server, 'none');
    socket.emit('unbanUser', {channelLoc: ROOMNAME, userUUID: uuid});
    return true;
}

function admin(username) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].admin();
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

function setAffiliation(username, affiliation) {
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].modifyAffiliation(username + '@' + server, affiliation);
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

function toggleMute() {
    var username = document.getElementById('newProfileBox').querySelector("span#profileBox-username").textContent;
    var iconSpan = document.getElementById('newProfileBox').querySelector('span#iconBar-muted');
    var muteButton = document.getElementById('newProfileBox').querySelector('button#profileBox-muteButton');
    if (CHATSTATUS.muteList.includes(username)) {
        unmute(username);
        muteButton.innerHTML = '<i class="fas fa-toggle-off"></i> Mute';
        iconSpan.style.display='none';
    } else {
        mute(username);
        muteButton.innerHTML = '<i class="fas fa-toggle-on"></i> Mute';
        iconSpan.style.display='inline';
    }
}

function modKick() {
    var username = document.getElementById('newProfileBox').querySelector("span#profileBox-username").textContent;
    kick(username);
    closeProfileBox();
}

function modBan() {
    var username = document.getElementById('newProfileBox').querySelector("span#profileBox-username").textContent;
    ban(username);
    closeProfileBox();
}

function modSetAffiliation(affiliation) {
    var username = document.getElementById('newProfileBox').querySelector("span#profileBox-username").textContent;
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].modifyAffiliation(affiliation);
    closeProfileBox();
}

function modSetRole(role) {
    var username = document.getElementById('newProfileBox').querySelector("span#profileBox-username").textContent;
    connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username].modifyRole(role);
    closeProfileBox();
}

// Generate Profile Box on Username Click
function displayProfileBox(elem) {
    closeProfileBox();
    var position = getPos(elem);
    var username = elem.textContent;
    var div = document.querySelector("div[data-type='profileBoxTemplate']").cloneNode(true);
    div.id="newProfileBox";

    // Check User Data for Icon Bar
    var xmppData = connection.muc.rooms[ROOMNAME + '@' + ROOM_SERVICE].roster[username];
    if (xmppData !== null && xmppData !== undefined) {
        // Affiliation Checks to Display Icon
        if (xmppData.affiliation === "owner") {
            div.querySelector("span#iconBar-owner").style.display = "inline";
        } else if (xmppData.affiliation === "admin") {
            div.querySelector("span#iconBar-admin").style.display = "inline";
        } else if (xmppData.affiliation === "member") {
            div.querySelector("span#iconBar-member").style.display = "inline";
        }

        // Role Checks to Display Icon
        if (xmppData.role === "moderator") {
            div.querySelector("span#iconBar-mod").style.display = "inline";
        } else if (xmppData.role === "participant") {
            div.querySelector("span#iconBar-voice").style.display = "inline";
        } else if (xmppData.role === "vistor") {
            div.querySelector("span#iconBar-visitor").style.display = "inline";
        }
    }

    // Check if Muted by User
    if  (CHATSTATUS.muteList.includes(username)) {
        div.querySelector("span#iconBar-muted").style.display = "inline";
        div.querySelector('button#profileBox-muteButton').innerHTML = '<i class="fas fa-toggle-on"></i> Mute';
    }

    openProfilebutton = div.querySelector('button#profileBox-openProfileButton');
    if ( /Guest[\d]+/.test(username) ) {
        openProfilebutton.style.disabled = true;
        openProfilebutton.classList.add('disabled');
    } else {
        destinationWindow = 'window.open("/profile/' + username + '", "OSP Profile","modal=yes,alwaysRaised=yes")';
        openProfilebutton.setAttribute('onclick', destinationWindow);
    }

    var modControlsBox = div.querySelector('div#profileBox-modControls');
    if (CHATSTATUS.role === "moderator") {
        // Prevent Owner from Showing Controls on Themselves
        if (!(username === CHATSTATUS['username'] && CHATSTATUS['affiliation'] === "owner")) {
            modControlsBox.style.display = "block";
        }
    }

    //Begin Async Call to Update Profile Data from API
    updateProfileBox(div, username);

    // Format ProfileBox
    div.style.position = 'absolute';
    div.style.top =  (position.y - ChatContentWindow.scrollTop) + "px";
    div.style.left = position.x + "px";
    div.style.zIndex = 10;
    div.style.display= "block";

    // Add to Document Body
    document.body.appendChild(div);
}

// Close Profile Box
function closeProfileBox() {
  var profileBox = document.getElementById('newProfileBox');
  if (profileBox != null) {
    document.getElementById('newProfileBox').remove();
  }
}

function updateProfileBox(elem, username) {
    var apiEndpoint = '/apiv1/user/' + username;

    // Retreive API Profile from OSP
    fetch(apiEndpoint) // Call the fetch function passing the url of the API as a parameter
    .then((resp) => resp.json())
    .then(function (data) {
        var profileData = data['results'];
        if (profileData.length > 0) { // Check if user exists
            elem.querySelector("span#profileBox-username").textContent = profileData[0]['username'];
            var pictureData = profileData[0]['pictureLocation'];
            if (pictureData !== null && pictureData !== '/images/None' && pictureData !== 'None') { // Check for invalid profile picture location
                // Set Picture if Valid
                elem.querySelector("img#profileBox-photo").src = pictureData;
            }
        } else {
            elem.querySelector("span#profileBox-username").textContent = username;
        }
    })
    .catch(function(error) {
        console.log('Unable to get api: ' + apiEndpoint);
        console.log(error);
    });
}

// Get Position to Generate Location for Profile Box
function getPos(el) {
    for (var lx=0, ly=0;
         el != null;
         lx += el.offsetLeft, ly += el.offsetTop, el = el.offsetParent);
    return {x: lx,y: ly};
}