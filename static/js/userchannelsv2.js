// User Channels Setup
var conn_options = {'sync disconnect on unload':true};
var socket = io();

Dropzone.autoDiscover = false;

var clipplayer = videojs('videoClip', { autoplay: false });
var ssplayer = videojs('videoSSClip', { autoplay: false });
var clipssplayer = videojs('clipSS', { autoplay: false });

var easymdeVideoEditor = new EasyMDE({ autoDownloadFontAwesome: false, spellChecker: false, element: document.getElementById("editVideoDescription")});
var easymdeVideoClip = new EasyMDE({ autoDownloadFontAwesome: false, spellChecker: false, element: document.getElementById("clipDescription")});
var easymdeClipEditor = new EasyMDE({ autoDownloadFontAwesome: false, spellChecker: false, element: document.getElementById("clipEditDescription")});
var newChanMDE = new EasyMDE({ autoDownloadFontAwesome: false, spellChecker: false, element: document.getElementById("description") });

// Initialize CodeMirror
var webhookHeaderElm = document.getElementById('webhookHeader');
var webhookBodyElm = document.getElementById('webhookPayload');
var webhookHeaderCodeMirror = CodeMirror.fromTextArea(webhookHeaderElm, {
    lineNumbers: true,
    matchBrackets: true,
    autoCloseBrackets: true,
    mode: "application/json",
    lineWrapping: true,
    autoRefresh:true,
    gutters: ["CodeMirror-lint-markers"],
    theme: 'material-darker',
    lint: true
});
var webhookBodyCodeMirror = CodeMirror.fromTextArea(webhookBodyElm, {
    lineNumbers: true,
    matchBrackets: true,
    autoCloseBrackets: true,
    mode: "application/json",
    lineWrapping: true,
    autoRefresh:true,
    gutters: ["CodeMirror-lint-markers"],
    theme: 'material-darker',
    lint: true
});
webhookHeaderCodeMirror.refresh();
webhookBodyCodeMirror.refresh();


// Event Listeners
webhookHeaderCodeMirror.on('change', function(cMirror) {
    webhookHeaderElm.value = cMirror.getValue();
});

webhookBodyCodeMirror.on('change', function(cMirror) {
    webhookBodyElm.value = cMirror.getValue();
});

window.addEventListener("beforeunload", function (e) {
  socket.emit('cancelUpload', { data: videofilename });
  return null;
});

$('#videoThumbnailUploadModal').on('hidden.bs.modal', function () {
    socket.emit('cancelUpload', { data: videofilename });
});

$('#videoClipModal').on('hidden.bs.modal', function () {
    clipplayer.pause();
});

$('#videoNewSSModal').on('hidden.bs.modal', function () {
    ssplayer.pause();
});

$(document).on("click", ".videoShareModalButton", function () {
    var videoID = $(this).data('videoid');
    $("#FBShareBtn").attr("onclick","window.open('https://www.facebook.com/sharer/sharer.php?u=" + siteProtocol + siteAddress + "/play/" + videoID + "','facebook-share-dialog','width=626,height=436');return false;");
    $("#TwitterShareBtn").attr("onclick","window.open('https://twitter.com/share?url=" + siteProtocol + siteAddress + "/play/" + videoID + "&text=Check out this Video!','twitter-share-dialog','width=626,height=436');return false;");
    $("#embedURLInput").attr('value',"<iframe src='" + siteProtocol + siteAddress + "/play/" + videoID + "?embedded=True&autoplay=True' width=600 height=345></iframe>");
    $("#linkShareInput").attr('value',siteProtocol + siteAddress + "/play/" + videoID);
});

$(document).on("click", ".clipShareModalButton", function () {
    var clipID = $(this).data('clipid');
    $("#FBShareBtn").attr("onclick","window.open('https://www.facebook.com/sharer/sharer.php?u=" + siteProtocol + siteAddress + "/clip/" + clipID + "','facebook-share-dialog','width=626,height=436');return false;");
    $("#TwitterShareBtn").attr("onclick","window.open('https://twitter.com/share?url=" + siteProtocol + siteAddress + "/clip/" + clipID + "&text=Check out this Video!','twitter-share-dialog','width=626,height=436');return false;");
    $("#embedURLInput").attr('value',"<iframe src='" + siteProtocol + siteAddress + "/clip/" + clipID + "?embedded=True&autoplay=True' width=600 height=345></iframe>");
    $("#linkShareInput").attr('value',siteProtocol + siteAddress + "/clip/" + clipID);
});

$(document).on("click", ".videoEditModalButton", function () {

   var videoID = $(this).data('videoid');
   var videoName = document.getElementById('vidName-' + videoID).innerText;
   var videoTopic = document.getElementById('vidTopic-' + videoID).innerText;
   var videoDescription = document.getElementById('vidDescription-' + videoID).innerText;
   var videoAllowComments = document.getElementById('vidAllowComments-' + videoID).innerText;


   $("#editVideoID").val(videoID);
   $("#editVideoName").val(videoName);

   if ((videoAllowComments == "true") || (videoAllowComments == "True") || (videoAllowComments == "on")) {
       var videoAllowCommentCheckBox = document.getElementById("editVideoAllowComments");
       videoAllowCommentCheckBox.checked = true;
       videoAllowCommentCheckBox.parentElement.classList.remove("off");
   } else {
       var videoAllowCommentCheckBox = document.getElementById("editVideoAllowComments");
       videoAllowCommentCheckBox.checked = false;
       videoAllowCommentCheckBox.parentElement.classList.add("off");
   }

   $("#editVideoTopic").val(videoTopic);

   document.getElementById("editVideoDescription").value = videoDescription;
   easymdeVideoEditor.value(videoDescription);
   var doc = easymdeVideoEditor.codemirror.getDoc();
   doc.setValue(doc.getValue());

});

$('#vanityURL').on('change keydown paste input', function(){
      var vanityURLInputDiv = document.getElementById('vanityURL');
      var vanityURLData = vanityURLInputDiv.value;
      vanityURLData = vanityURLData.replace(/[^a-zA-Z0-9]/g, "");
      var vanityURLHintDiv = document.getElementById('vanityURLExample');
      vanityURLHintDiv.innerHTML = vanityURLData;
      vanityURLInputDiv.value = vanityURLData;
});

// SocketIO Handlers
socket.on('newWebhookAck', function (msg) {
    var webhookName = msg['webhookName'];
    var webhookURL = msg['requestURL'];
    var webhookHeader = msg['requestHeader'];
    var webhookPayload = msg['requestPayload'];
    var webhookRequestType = msg['requestType'];
    var webhookTrigger = msg['requestTrigger'];
    var webhookID = msg['requestID'];
    var channelID = msg['channelID'];

    var tableRef = document.getElementById('webhookTable-' + channelID).getElementsByTagName('tbody')[0];

    var newRow = tableRef.insertRow(tableRef.rows.length);
    newRow.id = 'webhookTableRow-' + webhookID;

    var webhookNameCell = newRow.insertCell(0);
    var endpointURLCell = newRow.insertCell(1);
    var requestTriggerCell = newRow.insertCell(2);
    var requestTypeCell = newRow.insertCell(3);
    var requestHeaderCell = newRow.insertCell(4);
    var requestPayloadCell = newRow.insertCell(5);
    var buttonCell = newRow.insertCell(6);

    webhookNameCell.id = "webhookRowName-" + webhookID;
    endpointURLCell.id = "webhookRowEndpoint-" + webhookID;
    requestTriggerCell.id = "webhookRowTrigger-" + webhookID;
    requestTypeCell.id = "webhookRowType-" + webhookID;
    requestHeaderCell.id = "webhookRowHeader-" + webhookID;
    requestPayloadCell.id = "webhookRowPayload-" + webhookID;

    endpointURLCell.style.display = 'none';
    requestTypeCell.style.display = 'none';
    requestHeaderCell.style.display = 'none';
    requestPayloadCell.style.display = 'none';

    var buttonText = '<button type="button" class="btn btn-sm btn-warning" onclick="editWebhook(\'' + webhookID + '\',\'' + channelID + '\')"><i class="fas fa-edit"></i></button> <button type="button" class="btn btn-sm btn-danger" onclick="deleteWebhookModal(\'' + webhookID + '\')"><i class="far fa-trash-alt"></i></button>';

    var triggerVal = 'Unknown';

    switch(webhookTrigger) {
      case 0:
        triggerVal = 'Stream Start';
        break;
      case 1:
        triggerVal = 'Stream End';
        break;
      case 2:
        triggerVal = 'Stream Viewer Join';
        break;
      case 3:
        triggerVal = 'Stream Viewer Upvote';
        break;
      case 4:
        triggerVal = 'Stream Name Change';
        break;
      case 5:
        triggerVal = 'Chat Message';
        break;
      case 6:
        triggerVal = 'New Video';
        break;
      case 7:
        triggerVal = 'Video Comment';
        break;
      case 8:
        triggerVal = 'Video Upvote';
        break;
      case 9:
        triggerVal = 'Video Name Change';
        break;
      case 'Channel Subscription':
        triggerVal = 10;
        break;
      default:
        triggerVal = 'Unknown';

    }

    webhookNameCell.appendChild(document.createTextNode(webhookName));
    endpointURLCell.appendChild(document.createTextNode(webhookURL));
    requestTriggerCell.appendChild(document.createTextNode(triggerVal));
    requestTypeCell.appendChild(document.createTextNode(webhookRequestType));
    requestHeaderCell.appendChild(document.createTextNode(webhookHeader));
    requestPayloadCell.appendChild(document.createTextNode(webhookPayload));
    buttonCell.innerHTML = buttonText;
    createNewBSAlert("Webhook Added", "Success");

});

socket.on('changeWebhookAck', function (msg) {
    var webhookName = msg['webhookName'];
    var webhookURL = msg['requestURL'];
    var webhookHeader = msg['requestHeader'];
    var webhookPayload = msg['requestPayload'];
    var webhookRequestType = msg['requestType'];
    var webhookTrigger = msg['requestTrigger'];
    var webhookID = msg['requestID'];

    webhookNameCell = document.getElementById('webhookRowName-' + webhookID);
    endpointURLCell = document.getElementById('webhookRowEndpoint-' + webhookID);
    requestTriggerCell = document.getElementById('webhookRowTrigger-' + webhookID);
    requestTypeCell = document.getElementById('webhookRowType-' + webhookID);
    requestHeaderCell = document.getElementById('webhookRowHeader-' + webhookID);
    requestPayloadCell = document.getElementById('webhookRowPayload-' + webhookID);

    var triggerVal = 'Unknown';

    switch(webhookTrigger) {
      case 0:
        triggerVal = 'Stream Start';
        break;
      case 1:
        triggerVal = 'Stream End';
        break;
      case 2:
        triggerVal = 'Stream Viewer Join';
        break;
      case 3:
        triggerVal = 'Stream Viewer Upvote';
        break;
      case 4:
        triggerVal = 'Stream Name Change';
        break;
      case 5:
        triggerVal = 'Chat Message';
        break;
      case 6:
        triggerVal = 'New Video';
        break;
      case 7:
        triggerVal = 'Video Comment';
        break;
      case 8:
        triggerVal = 'Video Upvote';
        break;
      case 9:
        triggerVal = 'Video Name Change';
        break;
      case 'Channel Subscription':
        triggerVal = 10;
        break;
      default:
        triggerVal = 'Unknown';
    }

    webhookNameCell.innerText = webhookName;
    endpointURLCell.innerText = webhookURL;
    requestTriggerCell.innerText = triggerVal;
    requestTypeCell.innerText = webhookRequestType;
    requestHeaderCell.innerText = webhookHeader;
    requestPayloadCell.innerText = webhookPayload;
    createNewBSAlert("Webhook Edited", "Success");
});

socket.on('newRestreamAck', function (msg) {
    var restreamName = msg['restreamName'];
    var restreamURL = msg['restreamURL'];
    var restreamID = msg['restreamID'];
    var channelID = msg['channelID'];

    var tableRef = document.getElementById('restreamTable-' + channelID).getElementsByTagName('tbody')[0];

    var newRow = tableRef.insertRow(tableRef.rows.length);
    newRow.id = 'restreamTableRow-' + restreamID;
    newRow.className = 'align-middle';

    var restreamNameCell = newRow.insertCell(0);
    var restreamURLCell = newRow.insertCell(1);
    var restreamEnableCell = newRow.insertCell(2);
    var buttonCell = newRow.insertCell(3);

    restreamNameCell.id = "restreamRowName-" + restreamID;
    restreamURLCell.id = "restreamRowURL-" + restreamID;

    var restreamEnableText = '<div class="form-check form-switch"><input type="checkbox" class="form-check-input" id="restreamEnableToggle-' + restreamID + '" name="restreamEnableToggle-' + restreamID + '" onchange="toggleRestream(\'' + restreamID +'\')"></div>';

    var buttonText = '<button type="button" class="btn btn-sm btn-danger" onclick="deleteRestream(\'' + restreamID + '\')"><i class="far fa-trash-alt"></i></button>';

    restreamNameCell.appendChild(document.createTextNode(restreamName));
    restreamURLCell.appendChild(document.createTextNode(restreamURL));
    restreamEnableCell.innerHTML = restreamEnableText;
    buttonCell.innerHTML = buttonText;
    createNewBSAlert("Restream Destination Added", "Success");

});

socket.on('invitedUserAck', function (msg) {
    var username = msg['username'];
    var addedDate = msg['added'];
    var expiration = msg['expiration'];
    var channelID = msg['channelID'];
    var inviteID = msg['id'];

    var tableRef = document.getElementById('invitedUsersTable-' + channelID).getElementsByTagName('tbody')[0];

    var newRow = tableRef.insertRow(tableRef.rows.length);
    newRow.id = 'invitedUserRow-' + inviteID;
    newRow.className = 'align-middle';

    var usernameCell = newRow.insertCell(0);
    var addedDateCell = newRow.insertCell(1);
    var expirationDateCell = newRow.insertCell(2);
    var usedCodeCell = newRow.insertCell(3);
    var buttonCell = newRow.insertCell(4);

    var buttonText = '<button type="button" class="btn btn-danger" onclick="deleteInvitedUser(\'' + inviteID + '\')"><i class="far fa-trash-alt"></i></button>';

    usernameCell.appendChild(document.createTextNode(username));
    addedDateCell.appendChild(document.createTextNode(addedDate));
    expirationDateCell.appendChild(document.createTextNode(expiration));
    buttonCell.innerHTML = buttonText;
    createNewBSAlert("Invite Created", "Success");
});

socket.on('newInviteCode', function (msg) {
    var code = msg['code'];
    var expiration = msg['expiration'];
    var channelID = msg['channelID'];

    var tableRef = document.getElementById('inviteCodeTable-' + channelID).getElementsByTagName('tbody')[0];

    var newRow = tableRef.insertRow(tableRef.rows.length);
    newRow.id = 'inviteCodeRow-' + code;
    newRow.className = 'align-middle';

    var codeCell = newRow.insertCell(0);
    var expirationCell = newRow.insertCell(1);
    var usesCell = newRow.insertCell(2);
    var buttonCell = newRow.insertCell(3);

    var codeCellText = '<div class="input-group mb-3"><div class="input-group-prepend"><button type="button" class="btn btn-primary" onclick="CopyInviteCode(\'inviteCodeRO-' + code + '\',\'code\')"><i class="fas fa-copy"></i></button>' +
        '<button type="button" class="btn btn-success" onclick="CopyInviteCode(\'inviteCodeRO-' + code + '\',\'link\')"><i class="fas fa-link"></i></button></div>' +
        '<input type="text" class="form-control" name="inviteCodeRO" id="inviteCodeRO-' + code + '" value="' + code + '" readonly aria-describedby="inviteCodeRO required"></div>';
    var buttonText = '<button type="button" class="btn btn-danger" onclick="deleteInviteCode(\''+ code + '\')"><i class="far fa-trash-alt"></i></button>';

    codeCell.innerHTML = codeCellText;
    expirationCell.appendChild(document.createTextNode(expiration));
    usesCell.appendChild(document.createTextNode('0'));
    buttonCell.innerHTML = buttonText;
});

socket.on('addMod', function (msg) {
    var mod = msg['mod'];
    var channelLoc = msg['channelLoc'];
    var username = msg['username'];
    $('#mods-' + channelLoc).append('<div class="row" id="mod-' + channelLoc + '-' + mod + '"><div class="col-xs-12 col-sm-12 col-md-12 col-lg-6"><p>' + username + '</p></div><div class="col-xs-12 col-sm-12 col-md-12 col-lg-6"><button type="button" class="btn btn-sm btn-danger" onclick="deleteMod(\'' + mod + '\', ' + '\'' + channelLoc + '\')"><i class="far fa-trash-alt"></i></button></div></div>');
    createNewBSAlert("Moderator permission granted to user", "Success");
});

socket.on('checkScreenShot', function (msg) {
    document.getElementById("newScreenShotImg").src = msg['thumbnailLocation'];
});

socket.on('checkClipScreenShot', function (msg) {
    document.getElementById("newClipScreenShotImg").src = msg['thumbnailLocation'];
});

socket.on('disconnect', function () {
  socket.emit('cancelUpload', { data: videofilename });
});

// Functions

function CopyAPI(divVal) {
    var copyText = document.getElementById(divVal);
    copyText.select();
    document.execCommand("copy");
}

function CopyInviteCode(divVal, type) {
    var copyText = document.getElementById(divVal).value;
    if (type == 'link') {
        copyText = siteProtocol + siteAddress + '/settings/user/addInviteCode?inviteCode=' + copyText;
    }

    var dummy = document.createElement("input");
    document.body.appendChild(dummy);
    dummy.setAttribute('value', copyText);
    dummy.select();
    document.execCommand("copy");
    document.body.removeChild(dummy);
}

function openChannelWindow(divID, windowName) {
    var openWindow = document.getElementById(windowName + '-' + divID);
    var statWindow = document.getElementById('statWindow-' + divID);
    var videoWindow = document.getElementById('videoWindow-' + divID);
    var clipWindow = document.getElementById('clipWindow-' + divID);
    var settingsWindow = document.getElementById('settingsWindow-' + divID);
    var chatSettingsWindow = document.getElementById('chatSettingsWindow-' + divID);

    statWindow.style.display = 'none';
    videoWindow.style.display = 'none';
    clipWindow.style.display = 'none';
    settingsWindow.style.display = 'none';
    chatSettingsWindow.style.display = 'none';

    openWindow.style.display = 'block';
}

function deleteChannelModal(channelID) {
    document.getElementById('deleteChannelID').value = channelID;
    $('#confirmDeleteChannelModal').modal('show');
}

function openVideoDeleteModal(videoId) {
    document.getElementById('videoDeleteIDSelector').value = videoId;
    openModal('videoDeleteModal');
}

function deleteChannel() {
    var channelID = document.getElementById('deleteChannelID').value;
    socket.emit('deleteChannel', {channelID: channelID});
    var channelTableRow = document.getElementById('channelEntry-' + channelID);
    channelTableRow.parentNode.removeChild(channelTableRow);
    var channelDashRow = document.getElementById('channelDash-' + channelID);
    channelDashRow.parentNode.removeChild(channelDashRow);
}

function deleteVideo() {
    videoID = document.getElementById('videoDeleteIDSelector').value;
    var videoEntry = document.getElementById('video-' + videoID);
    videoEntry.parentNode.removeChild(videoEntry);
    socket.emit('deleteVideo', {videoID: videoID});
    createNewBSAlert("Video Queued for Deletion", "Success");
}

function editVideoSubmit() {
    var editVideoIDInput = document.getElementById("editVideoID");
    var editVideoNameInput = document.getElementById("editVideoName");
    var editVideoTopicInput = document.getElementById("editVideoTopic");
    var editVideoDescriptionInput = document.getElementById("editVideoDescription");
    var editVideoAllowCommentsInput = document.getElementById("editVideoAllowComments");
    var videoID = editVideoIDInput.value;

    var topicInputText = editVideoTopicInput.options[editVideoTopicInput.selectedIndex].text;

    var videoDescription = easymdeVideoEditor.value();

    document.getElementById("vidName-" + videoID).innerText = editVideoNameInput.value;
    document.getElementById("vidTopic-" + videoID).innerText = editVideoTopicInput.value;
    document.getElementById("vidTopicText-" + videoID).innerText = topicInputText;
    document.getElementById("vidDescription-" + videoID).innerText = videoDescription;
    document.getElementById("vidAllowComments-" + videoID).innerText = editVideoAllowCommentsInput.checked;

    editVideoDescriptionInput.value = "";
    easymdeVideoEditor.value("");
    var doc = easymdeVideoEditor.codemirror.getDoc();
    doc.setValue(doc.getValue());

    var allowComments = "False";
    if (editVideoAllowCommentsInput.checked) {
        allowComments = "True";
    }

    socket.emit('editVideo', {videoID: videoID, videoName: editVideoNameInput.value, videoTopic: editVideoTopicInput.value, videoDescription: videoDescription, videoAllowComments: allowComments });
    createNewBSAlert("Video Metadata Edited", "Success");
}

function moveVideoSubmit() {
    var videoID = document.getElementById('moveVideoID').value;
    var destinationChannelInput = document.getElementById('moveToChannelInput');
    var destinationChannel = destinationChannelInput.options[destinationChannelInput.selectedIndex].value;

    $('#video-' + videoID).detach().prependTo('#videoList-' + destinationChannel);

    socket.emit('moveVideo', {videoID: videoID, destinationChannel: destinationChannel});
    createNewBSAlert("Video Moved", "Success");
}

function togglePublished(videoID) {
    socket.emit('togglePublished', {videoID: videoID});
}

function togglePublishedClip(clipID) {
    socket.emit('togglePublishedClip', {clipID: clipID});
}

function checkClipConstraints() {
    var startTime = document.getElementById('clipStartTime').value;
    var stopTime = document.getElementById('clipStopTime').value;
    var systemMaxClipLength = maxClipLength;
    var clipErrorDiv = document.getElementById('clipError');
    var clipSubmitButton = document.getElementById('clipSubmitButton');

    if (systemMaxClipLength < 301) {
          if ((startTime != "") && (stopTime != "")) {
                var clipLength = stopTime - startTime;
                if (clipLength > systemMaxClipLength) {
                  clipErrorDiv.innerHTML = "Clip is longer than the maximum allowed length of " + systemMaxClipLength + " seconds!";
                  clipErrorDiv.style.display = "block";
                  clipSubmitButton.disabled = true;
                } else if (startTime > stopTime) {
                  clipErrorDiv.innerHTML = "Stop Time can not be before Start Time";
                  clipErrorDiv.style.display = "block";
                  clipSubmitButton.disabled = true;
                } else {
                  clipErrorDiv.innerHTML = "";
                  clipErrorDiv.style.display = "none";
                  clipSubmitButton.disabled = false;

                }
          }
    }
}

function openClipModal(videoID,videoLocation) {
    clipplayer.pause();
    var startInput = document.getElementById('clipStartTime');
    startInput.value = null;
    var stopInput = document.getElementById('clipStopTime');
    stopInput.value = null;
    var clipName = document.getElementById('clipName');
    clipName.value = null;
    clipplayer.src(videoLocation);
    document.getElementById("clipVideoID").value = videoID;
    var clipDescriptionInput = document.getElementById('clipDescription');
    clipDescriptionInput.value = null;
    easymdeVideoClip.value("");
    easymdeVideoClip.codemirror.refresh();
    openModal('videoClipModal');
}

function setClipStart() {
    var startInput = document.getElementById('clipStartTime');
    startInput.value = clipplayer.currentTime();
    checkClipConstraints();
}

function setClipStop() {
    var stopInput = document.getElementById('clipStopTime');
    stopInput.value = clipplayer.currentTime();
    checkClipConstraints();
}

function createVideoClipSubmit() {
    clipplayer.pause();
    var videoID = document.getElementById("clipVideoID").value;
    var clipName = document.getElementById("clipName").value;
    var clipDescription = easymdeVideoClip.value();
    var clipStart = document.getElementById("clipStartTime").value;
    var clipStop = document.getElementById("clipStopTime").value;

    socket.emit('createClip', {videoID: videoID, clipName: clipName, clipDescription: clipDescription, clipStart: clipStart, clipStop:clipStop});
    createNewBSAlert("Clip Queued for Creation", "Success");
}

function editClipSubmit() {
    var editClipIDInput = document.getElementById("editClipID").value;
    var editClipNameInput = document.getElementById("editClipName").value;
    var editClipDescriptionInput = document.getElementById("clipEditDescription");

    var clipDescription = easymdeClipEditor.value();

    editClipDescriptionInput.value = "";
    easymdeClipEditor.value("");
    var doc = easymdeClipEditor.codemirror.getDoc();
    doc.setValue(doc.getValue());

    document.getElementById("clipName-" + editClipIDInput).innerText = editClipNameInput;
    document.getElementById("clipDescription-" + editClipIDInput).innerText = clipDescription;

    createNewBSAlert("Clip Metadata Edited", "Success");

    socket.emit('editClip', {clipID: editClipIDInput, clipName: editClipNameInput, clipDescription: clipDescription});
}

function deleteClip() {
    var clipID = document.getElementById('clipDeleteIDSelector').value;
    var clipEntry = document.getElementById('clip-' + clipID);
    clipEntry.parentNode.removeChild(clipEntry);
    socket.emit('deleteClip', {clipID: clipID});
    createNewBSAlert("Clip Queued for Deletion", "Success");
}

function addMod(channelLoc) {
    var addModTextInput = document.getElementById('addModText-' + channelLoc);
    var JID = addModTextInput.value;
    socket.emit('addMod', {JID: JID, channelLoc: channelLoc});
    addModTextInput.value = "";
}

function deleteMod(mod, channelLoc) {
    socket.emit('deleteMod', {JID: mod, channelLoc: channelLoc});
    var modRow = document.getElementById('mod-' + channelLoc + '-' + mod);
    modRow.parentNode.removeChild(modRow);
    createNewBSAlert("Moderator permission revoked", "Success");
}

function generateInviteCode() {
    var channelID = document.getElementById('inviteCodeChannelId').value;
    var newInviteTextInput = document.getElementById('newInviteCodeText');
    var newInviteElementInput = document.getElementById('newInviteCode');
    var daysToExpire = newInviteElementInput.value;
    var customInviteCode = newInviteTextInput.value;
    socket.emit('generateInviteCode', {chanID: channelID, daysToExpiration: daysToExpire, inviteCode: customInviteCode});
    newInviteElementInput.value = null;
    newInviteTextInput.value = "";
}

function newInviteCodeModal(channelID) {
    document.getElementById('inviteCodeChannelId').value = channelID;
    document.getElementById('newInviteCodeText').value = '';
    document.getElementById('newInviteCode').value = '';
    openModal('newInviteCodeModal');
}

function newInviteUserModal(channelID) {
    document.getElementById('inviteUserChannelId').value = channelID;
    document.getElementById('newInvitedUsername').value = '';
    document.getElementById('newInvitedUserDays').value = '';
    openModal('newInviteUserModal');
}

function addInvitedUser() {
    var channelID = document.getElementById('inviteUserChannelId').value;
    var invitedUsernameDiv = document.getElementById('newInvitedUsername');
    var invitedUsername = invitedUsernameDiv.value;
    var daystoExpireDiv = document.getElementById('newInvitedUserDays');
    var daystoExpire = daystoExpireDiv.value;

    socket.emit('addUserChannelInvite', {chanID: channelID, username: invitedUsername, daysToExpiration: daystoExpire});
}

function deleteInvitedUser(inviteID) {
    socket.emit('deleteInvitedUser', {inviteID: inviteID});
    var inviteUserRow = document.getElementById('invitedUserRow-' + inviteID);
    inviteUserRow.parentNode.removeChild(inviteUserRow);
    createNewBSAlert("Invite Removed", "Success");
}

function deleteInviteCode(code) {
    socket.emit('deleteInviteCode', {code: code});
    var inviteCodeRow = document.getElementById('inviteCodeRow-' + code);
    inviteCodeRow.parentNode.removeChild(inviteCodeRow);
    createNewBSAlert("Invite Code Removed", "Success");
}

function deleteWebhookModal(webhookID) {
    document.getElementById('deleteWebhookID').value = webhookID;
    $('#confirmDeleteWebhookModal').modal('show');
}

function deleteWebhook() {
    var webhookID = document.getElementById('deleteWebhookID').value;
    socket.emit('deleteWebhook', {webhookID: webhookID});
    var webhookTableRow = document.getElementById('webhookTableRow-' + webhookID);
    webhookTableRow.parentNode.removeChild(webhookTableRow);
    createNewBSAlert("Webhook Deleted", "Success");
}

function testWebhook(webhookID, channelID) {
    socket.emit('testWebhook', {webhookID: webhookID, channelID: channelID, webhookType: 'channel'});
    createNewBSAlert("Webhook Test Sent","success")
}

function openNewRestreamModal(chanID) {
    $('#newRestreamModal').modal('show');
    var restreamName = document.getElementById('restreamName');
    var restreamURL = document.getElementById('restreamURL');
    var restreamChannelID = document.getElementById('restreamChannelIDInput');

    restreamName.value = "";
    restreamURL.value = "";

    restreamChannelID.value = chanID;
}

function submitNewRestream() {
    var restreamName = document.getElementById('restreamName');
    var restreamURL = document.getElementById('restreamURL');
    var restreamChannelID = document.getElementById('restreamChannelIDInput');

    socket.emit('newRestream', {name: restreamName.value, restreamURL:restreamURL.value, restreamChannelID: restreamChannelID.value});
    createNewBSAlert("Restream Destination Created", "Success");
}

function toggleRestream(restreamID) {
    socket.emit('toggleRestream',{id:restreamID});
}

function deleteRestream(restreamID) {
    socket.emit('deleteRestream', {id:restreamID});
    var restreamTableRow = document.getElementById('restreamTableRow-' + restreamID);
    restreamTableRow.parentNode.removeChild(restreamTableRow);
    createNewBSAlert("Restream Destination Deleted", "Success");
}

function openNewWebhookModal(chanID) {
    $('#newWebhookModal').modal('show');
    var webhookName = document.getElementById('webhookName');
    var webhookEndpoint = document.getElementById('webhookEndpoint');
    var webhookHeader = document.getElementById('webhookHeader');
    var webhookPayload = document.getElementById('webhookPayload');
    var webhookReqTypeElement = (document.getElementById('webhookReqType'));
    var webhookTriggerElement = document.getElementById('webhookTrigger');
    var webhookChannelID = (document.getElementById('webhookChannelIDInput'));
    var webhookInputAction = document.getElementById('webhookInputAction');
    var webhookInputID = document.getElementById('webhookID');

    webhookInputID.value = 'New';

    webhookName.value = "";
    webhookEndpoint.value = "";
    webhookHeader.value = "";
    webhookPayload.value = "";
    webhookReqTypeElement.value = 0;
    webhookTriggerElement.value = 0;
    webhookChannelID.value = chanID;
    webhookInputAction.value = 'new';

    webhookHeaderCodeMirror.getDoc().setValue('{}');
    webhookHeaderCodeMirror.refresh();
    webhookBodyCodeMirror.getDoc().setValue('{}');
    webhookBodyCodeMirror.refresh();
}

function submitWebhook() {
    var webhookName = document.getElementById('webhookName').value;
    var webhookEndpoint = document.getElementById('webhookEndpoint').value;
    var webhookHeader = document.getElementById('webhookHeader').value;
    var webhookPayload = document.getElementById('webhookPayload').value;
    var webhookReqTypeElement = (document.getElementById('webhookReqType'));
    var webhookTriggerElement = document.getElementById('webhookTrigger');
    var webhookReqType = webhookReqTypeElement.options[webhookReqTypeElement.selectedIndex].value;
    var webhookTrigger = webhookTriggerElement.options[webhookTriggerElement.selectedIndex].value;
    var webhookChannelID = (document.getElementById('webhookChannelIDInput')).value;
    var webhookInputAction = document.getElementById('webhookInputAction').value;
    var webhookInputID = document.getElementById('webhookID').value;

    if (webhookName == '') {
        (document.getElementById('webhookName')).setCustomValidity('Name is Required');
    }
    if (webhookEndpoint == '') {
        (document.getElementById('webhookEndpoint')).setCustomValidity('Endpoint URL is Required');
    }

    socket.emit('submitWebhook', {webhookName: webhookName, webhookEndpoint: webhookEndpoint, webhookHeader:webhookHeader, webhookPayload:webhookPayload, webhookReqType: webhookReqType, webhookTrigger: webhookTrigger, webhookChannelID:webhookChannelID, inputAction:webhookInputAction, webhookInputID:webhookInputID});
}

function editWebhook(webhookID, chanID) {
    var webHookChannelIDInput = document.getElementById('webhookChannelIDInput');
    var webhookTrigger = document.getElementById('webhookTrigger');
    var webhookName = document.getElementById('webhookName');
    var webhookEndpoint = document.getElementById('webhookEndpoint');
    var webhookHeader = document.getElementById('webhookHeader');
    var webhookPayload = document.getElementById('webhookPayload');
    var webhookReqTypeElement = document.getElementById('webhookReqType');
    var webhookInputAction = document.getElementById('webhookInputAction');
    var webhookInputID = document.getElementById('webhookID');

    var triggerVal = document.getElementById('webhookRowTrigger-' + webhookID).innerText;

    switch(triggerVal) {
      case 'Stream Start':
        triggerVal = 0;
        break;
      case 'Stream End':
        triggerVal = 1;
        break;
      case 'Stream Viewer Join':
        triggerVal = 2;
        break;
      case 'Stream Viewer Upvote':
        triggerVal = 3;
        break;
      case 'Stream Name Change':
        triggerVal = 4;
        break;
      case 'Chat Message':
        triggerVal = 5;
        break;
      case 'New Video':
        triggerVal = 6;
        break;
      case 'Video Comment':
        triggerVal = 7;
        break;
      case 'Video Upvote':
        triggerVal = 8;
        break;
      case 'Video Name Change':
        triggerVal = 9;
        break;
      case 'Channel Subscription':
        triggerVal = 10;
        break;
      default:
        triggerVal = 0;
    }

    webhookName.value = document.getElementById('webhookRowName-' + webhookID).innerText;
    webhookEndpoint.value = document.getElementById('webhookRowEndpoint-' + webhookID).innerText;
    webhookHeader.value = document.getElementById('webhookRowHeader-' + webhookID).innerText;
    webhookPayload.value = document.getElementById('webhookRowPayload-' + webhookID).innerText;
    webhookReqTypeElement.value = document.getElementById('webhookRowType-' + webhookID).innerText;
    webhookTrigger.value = triggerVal;
    webHookChannelIDInput.value = chanID;
    webhookInputAction.value = 'edit';
    webhookInputID.value = webhookID;

    webhookHeaderCodeMirror.getDoc().setValue(webhookHeader.value);
    webhookHeaderCodeMirror.refresh();
    webhookBodyCodeMirror.getDoc().setValue(webhookPayload.value);
    webhookBodyCodeMirror.refresh();

    $('#newWebhookModal').modal('show');
    webhookHeader.value = JSON.stringify(JSON.parse(webhookHeader.value), undefined, 2);
    webhookPayload.value = JSON.stringify(JSON.parse(webhookPayload.value), undefined, 2);
}

function saveUploadedThumbnail() {
    var videoID = document.getElementById('videoThumbnailID').value;
    var thumbnailType = document.getElementById('videoThumbnailType').value;
    var thumbnailDiv;
    if (thumbnailType === 'video') {
        socket.emit('saveUploadedThumbnail', {videoID: videoID, thumbnailFilename: videofilename + '.png'});
        thumbnailDiv = document.getElementById('videoThumb-' + videoID);
    } else if (thumbnailType === 'clip') {
        socket.emit('saveUploadedThumbnail', {clipID: videoID, thumbnailFilename: videofilename + '.png'});
        thumbnailDiv = document.getElementById('clipThumb-' + videoID);
    }
    var thumbnailURL = thumbnailDiv.src;
    setTimeout(function() {
        thumbnailDiv.src = thumbnailURL + '?t=' + new Date().getTime();
    }, 4000);
    createNewBSAlert("Thumbnail Updated", "Success");
}

function openClipSSModal(clipID, videoID, videoLocation) {
    clipssplayer.pause();

    clipssplayer.src(videoLocation);
    clipssplayer.load();

    document.getElementById("clipssID").value = clipID;
    document.getElementById("clipvideossID").value = videoID;

    document.getElementById("newClipScreenShotImg").src = "/static/img/video-placeholder.jpg";
    openModal('clipNewSSModal');
}

function openSSModal(videoID,videoLocation) {
    ssplayer.pause();
    ssplayer.src(videoLocation);
    document.getElementById("videossID").value = videoID;
    document.getElementById("newScreenShotImg").src = "/static/img/video-placeholder.jpg";
    openModal('videoNewSSModal');
}

function newScreenShot() {
    ssplayer.pause();
    window.whereYouAt = ssplayer.currentTime();
    document.getElementById("SSTimestamp").value = window.whereYouAt;
    socket.emit('newScreenShot', { loc: document.getElementById('videossID').value, timeStamp: window.whereYouAt });
}

function newClipScreenShot() {
    clipssplayer.pause();
    window.whereYouAt = clipssplayer.currentTime();
    document.getElementById("clipSSTimestamp").value = window.whereYouAt;
    socket.emit('newScreenShot', { loc: document.getElementById('clipvideossID').value, 'clipID': document.getElementById('clipssID').value, timeStamp: window.whereYouAt, clip:true });
}

function setScreenShot() {
    var timestamp = document.getElementById("SSTimestamp").value;
    socket.emit('setScreenShot', { loc: document.getElementById('videossID').value, timeStamp: timestamp });
    var videoID = document.getElementById('videossID').value;
    ssplayer.pause();
    setTimeout(function() {
        document.getElementById('videoThumb-' + videoID).src = document.getElementById('videoThumb-' + videoID).src + '?t=' + new Date().getTime();
        }, 4000);
    createNewBSAlert("Thumbnail Updated", "Success");
}

function setClipScreenShot() {
    var timestamp = document.getElementById("clipSSTimestamp").value;
    socket.emit('setScreenShot', { clipID: document.getElementById('clipssID').value, timeStamp: timestamp });
    var clipID = document.getElementById('clipssID').value;
    clipssplayer.pause();
    setTimeout(function() {
        document.getElementById('clipThumb-' + clipID).src = document.getElementById('clipThumb-' + clipID).src + '?t=' + new Date().getTime();
        }, 4000);
    createNewBSAlert("Thumbnail Updated", "Success");
}

function newStickerModal(channelID) {
    document.getElementById('stickerChannelID').value = channelID;
    $('#newStickerModal').modal('show');
}


function deleteStickerModal(stickerID, channelID) {
    document.getElementById('deleteStickerID').value = stickerID;
    document.getElementById('deleteStickerChannelID').value = channelID
    $('#deleteStickerModal').modal('show');
}

function deleteSticker() {
    stickerID = document.getElementById('deleteStickerID').value;
    channelID = document.getElementById('deleteStickerChannelID').value
    socket.emit('deleteSticker', {stickerID: stickerID, channelID: channelID});
    stickerDiv = document.getElementById('sticker-' + stickerID);
    stickerDiv.parentNode.removeChild(stickerDiv);
    document.getElementById('deleteStickerID').value = "";
    createNewBSAlert("Sticker Deleted","success")
}

function editStickerModal(stickerID, channelID) {
    stickerName = document.getElementById('sticker-name-' + stickerID).value;
    socket.emit('editSticker', {stickerID: stickerID, stickerName: stickerName, channelID: channelID});
    createNewBSAlert("Sticker Edited","success")
}

function moveVideoModal(videoId) {
    document.getElementById('moveVideoID').value=videoId;
    document.getElementById('moveToChannelInput').selectedIndex =0;
    openModal('videoMoveModal')
}

function uploadThumbnailModal(videoId, type) {
    if (type === 'video') {
        document.getElementById('videothumbnailuploadpreview').src = document.getElementById('videoThumb-' + videoId).src;
    } else if (type === 'clip') {
        document.getElementById('videothumbnailuploadpreview').src = document.getElementById('clipThumb-' + videoId).src;
    } else {
        document.getElementById('videothumbnailuploadpreview').src = '/static/img/video-placeholder.jpg';
    }

    videofilename = s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();
    document.getElementById('videoThumbnailID').value = videoId;
    document.getElementById('videoThumbnailType').value = type;
    document.getElementById('videothumbnailFilenameDisplay').value = '';
    document.getElementById('videothumbnailFilename').value = '';
    openModal('videoThumbnailUploadModal')
}

function editClipMetadataModal(clipID) {

   var clipName = document.getElementById('clipName-' + clipID).innerText;
   var clipDescription = document.getElementById('clipDescription-' + clipID).innerText;

   $("#editClipID").val(clipID);
   $("#editClipName").val(clipName);

   document.getElementById("clipEditDescription").value = clipDescription;
   easymdeClipEditor.value(clipDescription);
   var doc = easymdeClipEditor.codemirror.getDoc();
   doc.setValue(doc.getValue());
   openModal('clipEditModal');
}

function deleteClipModal(clipID) {
    document.getElementById('clipDeleteIDSelector').value = clipID;
    openModal('clipDeleteModal');
}