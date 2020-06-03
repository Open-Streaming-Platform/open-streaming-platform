// SimpleMDE Initialization
var simplemde1 = new EasyMDE({ autoDownloadFontAwesome: false, spellChecker: false, element: document.getElementById("serverMessage") });

// Input Handlers
$('#restoreData').on('change',function(){
    //get the file name
    var fileName = $(this).val();
    //replace the "Choose a file" label
    $(this).next('.custom-file-label').html(fileName);
})

$(document).on("click", ".edit-oAuth-Button", function () {
     var oAuthID = $(this).data('id');
     var oAuthName = $(this).data('name');
     var oAuthType = $(this).data('authtype');
     var oAuthFriendlyName = $(this).data('friendlyname');
     var oAuthDisplayColor = $(this).data('displaycolor');
     var oAuthClientID = $(this).data('clientid');
     var oAuthClientSecret = $(this).data('clientsecret');
     var oAuthAccessTokenURL = $(this).data('accesstokenurl');
     var oAuthAccessTokenParams = $(this).data('accesstokenparams');
     var oAuthAuthorizeURL = $(this).data('authorizeurl');
     var oAuthAuthorizeParams = $(this).data('authorizeparams');
     var oAuthAPIBaseURL = $(this).data('apibaseurl');
     var oAuthClientKwargs = $(this).data('clientkwargs');
     var oAuthProfileEndpoint = $(this).data('profileendpoint');
     var oAuthIDValue= $(this).data('idvalue');
     var oAuthUsername = $(this).data('usernamevalue');
     var oAuthEmail = $(this).data('emailvalue');
     $("#oAuthID").val( oAuthID );
     $("#oAuthPreset").val( oAuthType )
     $("#oAuthName").val( oAuthName );
     $("#oAuthFriendlyName").val( oAuthFriendlyName );
     $("#oAuthColor").val( oAuthDisplayColor );
     $("#oAuthClient_id").val( oAuthClientID );
     $("#oAuthClient_secret").val( oAuthClientSecret );
     $("#oAuthAccess_token_url").val( oAuthAccessTokenURL );
     if (oAuthAccessTokenParams != 'None') {
         $("#oAuthAccess_token_params").val(JSON.parse(oAuthAccessTokenParams));
     }
     $("#oAuthAuthorize_url").val( oAuthAuthorizeURL );
     if (oAuthAuthorizeParams != 'None') {
         $("#oAuthAuthorize_params").val(JSON.parse(oAuthAuthorizeParams));
     }
     $("#oAuthApi_base_url").val( oAuthAPIBaseURL );
     if (oAuthClientKwargs != 'None') {
         $("#oAuthClient_kwargs").val(JSON.parse(oAuthClientKwargs));
     }
     $("#oAuthProfile_endpoint").val( oAuthProfileEndpoint );
     $("#oAuthIDValue").val( oAuthIDValue );
     $("#oAuthUsername").val( oAuthUsername );
     $("#oAuthEmail").val( oAuthEmail );
     updateOAuthModalWindowLayout();
     $("#newOauthModal").modal('show');
});

$('#search').on('input', function(){
    var query = document.getElementById("search").value.toLowerCase();
    $('.searchable').each(function(){
         var $this = $(this);
         if($this.text().toLowerCase().indexOf(query) === -1)
             $this.closest('.searchable').hide();
        else $this.closest('.searchable').show();
    });
});

$('.rangeSliderInput').on('input', function() {
  var sliderValue = $(this).val();
  if (sliderValue != "") {
    var maxValue = $(this).attr("max");
    if (sliderValue != maxValue) {
      var date = new Date(0);
      date.setSeconds(sliderValue);
      var timeString = date.toISOString().substr(11, 8);
    } else {
      timeString = "Infinite";
    }
    $(this).siblings("h3").find('.rangeSliderValue')[0].innerHTML = timeString;
  }
});

// Set Presets for oAuth
$(document).on("change", "#oAuthPreset", function () {
    updateOAuthModalWindowLayout();
});

// SocketIO Config
var conn_options = {'sync disconnect on unload':true};
var socket = io();

// Establish Intervals
setInterval(function() {
  socket.emit('getServerResources',{data:"0"});
  console.log('Sent Resource Request')
},10000 );

// SocketIO Functions
socket.on('connect', function() {
    socket.emit('getServerResources',{data:"0"});
    console.log('Sent Resource Request')
});

socket.on('serverResources', function(msg) {
    $('#cpuUsage').attr('aria-valuenow', msg['cpuUsage']).css('width',msg['cpuUsage'] + '%');
    $('#cpuUsage').text(msg['cpuUsage'] + '%');
    $('#cpuStats').text(msg['cpuLoad']);

    $('#memoryUsage').attr('aria-valuenow', msg['memoryUsage']).css('width',msg['memoryUsage'] + '%');
    $('#memoryUsage').text(msg['memoryUsage'] + '%');
    $('#memoryStats').text(msg['memoryUsageAvailable'] + ' MB / ' + msg['memoryUsageTotal'] + ' MB');

    $('#diskUsage').attr('aria-valuenow', msg['diskUsage']).css('width',msg['diskUsage'] + '%');
    $('#diskUsage').text(msg['diskUsage'] + '%');
    $('#diskStats').text(msg['diskFree'] + ' MB / ' + msg['diskTotal'] + ' MB');
});

socket.on('edgeNodeCheckResults', function (msg) {
    var edgeID = msg['edgeID'];
    var edgeStatus = Number(msg['status']);
    var nodeStatusDiv = document.getElementById('nodeStatus-' + edgeID);

    var newSpan;

    if (edgeStatus == 0) {
        newSpan = '<span class="badge badge-danger">Offline</span>';
    } else if (edgeStatus == 1) {
        newSpan = '<span class="badge badge-success">Online</span>';
    }

    nodeStatusDiv.innerHTML = newSpan;
});

socket.on('newGlobalWebhookAck', function (msg) {
    var webhookName = msg['webhookName'];
    var webhookURL = msg['requestURL'];
    var webhookHeader = msg['requestHeader'];
    var webhookPayload = msg['requestPayload'];
    var webhookRequestType = msg['requestType'];
    var webhookTrigger = msg['requestTrigger'];
    var webhookID = msg['requestID'];

    var tableRef = document.getElementById('webhookTable').getElementsByTagName('tbody')[0];

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

    var buttonText = '<button type="button" class="btn btn-sm btn-warning" onclick="editWebhook(\'' + webhookID + '\')"><i class="fas fa-edit"></i></button> <button type="button" class="btn btn-sm btn-danger" onclick="deleteWebhookModal(\'' + webhookID + '\')"><i class="far fa-trash-alt"></i></button>';

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
      case 20:
        triggerVal = 'New User';
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
});

socket.on('changeGlobalWebhookAck', function (msg) {
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
      case 20:
        triggerVal = 'New User';
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
});

socket.on('testEmailResults', function(msg) {
    var results = msg['results'];
    if (results == "True") {
        document.getElementById("emailsuccess").style.display = "Block";
    } else if (results == "False") {
        document.getElementById("emailfailure").style.display = "Block";
    }
});

// Functions

function testEmail(){
    smtpAddress = document.getElementById("smtpAddress").value;
    smtpPort = document.getElementById("smtpPort").value;
    smtpTLS = document.getElementById("smtpTLS").checked;
    smtpSSL = document.getElementById("smtpSSL").checked;
    smtpUser = document.getElementById("smtpUser").value;
    smtpPassword = document.getElementById("smtpPassword").value;
    smtpSender = document.getElementById("smtpSendAs").value;

    document.getElementById("emailsuccess").style.display = "None";
    document.getElementById("emailfailure").style.display = "None";

    socket.emit('testEmail', {smtpServer:smtpAddress, smtpPort:smtpPort, smtpTLS: smtpTLS, smtpSSL:smtpSSL, smtpUsername:smtpUser, smtpPassword:smtpPassword, smtpSender:smtpSender, smtpReceiver:smtpSender});
}

function deleteOAuthProvider(providerID) {
    document.getElementById('DeleteOAuthProviderID').value = providerID;
    $('#deleteOauthModal').modal('show');
}

function updateOAuthModalWindowLayout() {
    var authType = document.getElementById("oAuthPreset").value;
    switch(authType) {
        case "Custom":
            $("#oAuthAccess_token_url").attr("disabled", false);
            $("#oAuthAccess_token_urlDiv").show();
            $("#oAuthAccess_token_params").attr("disabled", false);
            $("#oAuthAccess_token_paramsDiv").show();
            $("#oAuthAuthorize_url").attr("disabled", false);
            $("#oAuthAuthorize_urlDiv").show();
            $("#oAuthAuthorize_params").attr("disabled", false);
            $("#oAuthAuthorize_paramsDiv").show();
            $("#oAuthApi_base_url").attr("disabled", false);
            $("#oAuthApi_base_urlDiv").show();
            $("#oAuthClient_kwargs").attr("disabled", false);
            $("#oAuthClient_kwargsDiv").show();
            $("#oAuthProfile_endpoint").attr("disabled", false);
            $("#oAuthProfile_endpointDiv").show();
            $("#oAuthIDValue").attr("disabled", false);
            $("#oAuthIDValueDiv").show();
            $("#oAuthUsername").attr("disabled", false);
            $("#oAuthUsernameDiv").show();
            $("#oAuthEmail").attr("disabled", false);
            $("#oAuthEmailDiv").show();
            break;
        default:
            $("#oAuthAccess_token_url").attr("disabled", true);
            $("#oAuthAccess_token_urlDiv").hide();
            $("#oAuthAccess_token_params").attr("disabled", true);
            $("#oAuthAccess_token_paramsDiv").hide();
            $("#oAuthAuthorize_url").attr("disabled", true);
            $("#oAuthAuthorize_urlDiv").hide();
            $("#oAuthAuthorize_params").attr("disabled", true);
            $("#oAuthAuthorize_paramsDiv").hide();
            $("#oAuthApi_base_url").attr("disabled", true);
            $("#oAuthApi_base_urlDiv").hide();
            $("#oAuthClient_kwargs").attr("disabled", true);
            $("#oAuthClient_kwargsDiv").hide();
            $("#oAuthProfile_endpoint").attr("disabled", true);
            $("#oAuthProfile_endpointDiv").hide();
            $("#oAuthIDValue").attr("disabled", true);
            $("#oAuthIDValueDiv").hide();
            $("#oAuthUsername").attr("disabled", true);
            $("#oAuthUsernameDiv").hide();
            $("#oAuthEmail").attr("disabled", true);
            $("#oAuthEmailDiv").hide();
            break;
    }
}

function resetOAuthForm() {
    document.getElementById("OAuthForm").reset();
    $("#oAuthID").val('');
    updateOAuthModalWindowLayout();
}

function deleteEdge(edgeID) {
    socket.emit('deleteOSPEdge', {edgeID: edgeID});
    var edgeTableRow = document.getElementById('edgeTableRow-' + edgeID);
    edgeTableRow.parentNode.removeChild(edgeTableRow);
}

function toggleActiveEdge(edgeID) {
    socket.emit('toggleOSPEdge', {edgeID: edgeID});
}

function checkEdge(edgeID) {
    var oldStatusDiv = document.getElementById('nodeStatus-' + edgeID);
    oldStatusDiv.innerHTML = '<span id="nodeStatus-' + edgeID + '"><div class="spinner-border" role="status"><span class="sr-only">Loading...</span></div></span>';
    socket.emit('checkEdge', {edgeID: edgeID});
}

function openNewWebhookModal() {
    $('#newWebhookModal').modal('show');
    var webhookName = document.getElementById('webhookName');
    var webhookEndpoint = document.getElementById('webhookEndpoint');
    var webhookHeader = document.getElementById('webhookHeader');
    var webhookPayload = document.getElementById('webhookPayload');
    var webhookReqTypeElement = (document.getElementById('webhookReqType'));
    var webhookTriggerElement = document.getElementById('webhookTrigger');
    var webhookInputAction = document.getElementById('webhookInputAction');
    var webhookInputID = document.getElementById('webhookID');

    webhookInputID.value = 'New';
    webhookName.value = "";
    webhookEndpoint.value = "";
    webhookHeader.value = "";
    webhookPayload.value = "";
    webhookReqTypeElement.value = 0;
    webhookTriggerElement.value = 0;
    webhookInputAction.value = 'new';
}

function deleteWebhookModal(webhookID) {
    document.getElementById('deleteWebhookID').value = webhookID;
    $('#confirmDeleteWebhookModal').modal('show');
}

function deleteWebhook() {
    var webhookID = document.getElementById('deleteWebhookID').value;
    socket.emit('deleteGlobalWebhook', {webhookID: webhookID});
    var webhookTableRow = document.getElementById('webhookTableRow-' + webhookID);
    webhookTableRow.parentNode.removeChild(webhookTableRow);
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
    var webhookInputAction = document.getElementById('webhookInputAction').value;
    var webhookInputID = document.getElementById('webhookID').value;

    if (webhookName == '') {
        (document.getElementById('webhookName')).setCustomValidity('Name is Required');
    }
    if (webhookEndpoint == '') {
        (document.getElementById('webhookEndpoint')).setCustomValidity('Endpoint URL is Required');
    }
    socket.emit('submitGlobalWebhook', {webhookName: webhookName, webhookEndpoint: webhookEndpoint, webhookHeader:webhookHeader, webhookPayload:webhookPayload, webhookReqType: webhookReqType, webhookTrigger: webhookTrigger, inputAction:webhookInputAction, webhookInputID:webhookInputID});
}

function editWebhook(webhookID) {
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
      case 'New User':
        triggerVal = 20;
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
    webhookInputAction.value = 'edit';
    webhookInputID.value = webhookID;

    $('#newWebhookModal').modal('show');
    webhookHeader.value = JSON.stringify(JSON.parse(webhookHeader.value), undefined, 2);
    webhookPayload.value = JSON.stringify(JSON.parse(webhookPayload.value), undefined, 2);
}

function testWebhook(webhookID) {
    socket.emit('testWebhook', {webhookID: webhookID, webhookType: 'global'});
    createNewBSAlert("Webhook Test Sent","success")
}

function deleteChannelModal(channelID) {
    document.getElementById('deleteChannelID').value = channelID;
    $('#confirmDeleteChannelModal').modal('show');
}

function deleteChannel() {
    var channelID = document.getElementById('deleteChannelID').value;
    socket.emit('deleteChannel', {channelID: channelID});
    var channelTableRow = document.getElementById('channelCardRow-' + channelID);
    channelTableRow.parentNode.removeChild(channelTableRow);
}

function openStreamDeleteModal(streamID) {
    document.getElementById('deleteStreamID').value = streamID;
    $('#deleteStreamModal').modal('show');
}

function deleteStream() {
    var streamID = document.getElementById('deleteStreamID').value;
    socket.emit('deleteStream', {streamID: streamID});
    var streamCard = document.getElementById('streamCard-' + streamID);
    streamCard.parentNode.removeChild(streamCard);
    document.getElementById('deleteStreamID').value = "";
}

function toggleDiv(selDiv){
    var divid = '#' + selDiv;
    $('.settingsOption').hide();
    $(divid).show();
}