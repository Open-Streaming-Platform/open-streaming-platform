// Socket.IO Connection
var conn_options = {'sync disconnect on unload':true};
var socket = io();

// Admin Page Viewer Chart
var ctx = document.getElementById('viewershipChart').getContext('2d');
//ctx.canvas.width = viewerChartWidth;
//ctx.canvas.height = viewerChartHeight;
var chart = new Chart(ctx, {
    responsive:false,
    maintainAspectRatio: false,
    // The type of chart we want to create
    type: 'bar',

    // The data for our dataset
    data: {
        datasets: [
            {
            label: "Live Viewers",
            fill: true,
            borderColor: 'rgb(40, 90, 150)',
            backgroundColor: 'rgb(40, 90, 150)',
            spanGaps: true,
            lineTension: 0,
            data: viewerChartDataLive
            },
            {
            label: "Video Viewers",
            fill: true,
            borderColor: 'rgb(90, 150, 40)',
            backgroundColor: 'rgb(90, 150, 40)',
            spanGaps: true,
            lineTension: 0,
            data:viewerChartDataVideo
        }]
    },

    // Configuration options go here
    options: {
        scales: {
            xAxes: [{
                type: 'time',
                time: {
                    parser: 'YYYY-MM-DD',
                    unit: 'day'
                }
            }],
        }
    }
});

// Sets the Front Page Panel Layout Object to be Sortable
var frontPagePanelSortList = document.getElementById('panelOrderList');
var frontPagePanelSortableObject = Sortable.create(frontPagePanelSortList, {
  animation: 350
});

$('#maxClipLength').on('input', function() {
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

// oAuth Related JS
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

// Set Presets for oAuth
$(document).on("change", "#oAuthPreset", function () {
    updateOAuthModalWindowLayout();
});

// SocketIO Handlers
socket.on('connect', function() {
    console.log('Connected to SocketIO');
    get_all_osp_component_status();
});

socket.on('admin_osp_component_status_update', function (msg) {
    var componentStatusName = msg['component'];
    var status = msg['status'];

    console.log('Received Component Update - ' + componentStatusName);
    componentIDDiv = document.getElementById('component-status_' + componentStatusName);

    var html = ''
    if (status === 'OK') {
        html = '<i class="text-success fas fa-check" title="' + msg['message'] + '"></i>'
    } else if (status === 'Problem') {
        html = '<i class="text-warning fas fa-exclamation-triangle" title="' + msg['message'] + '"></i>'
    } else {
        html = '<i class="text-danger fas fa-times" title="' + msg['message'] + '"></i>'
    }
    componentIDDiv.innerHTML = html;
    console.log(msg['message']);
});

function testPageLayoutArray() {
  var panelListItems = document.getElementById('panelOrderList').getElementsByTagName('li'),
  panelListArray = map(panelListItems, getNodeIds);
  console.log(panelListArray);
}

function updateSlider(inputID) {
    var sliderValue = $(inputID).val();
      if (sliderValue != "") {
        var maxValue = $(inputID).attr("max");
        if (sliderValue != maxValue) {
          var date = new Date(0);
          date.setSeconds(sliderValue);
          var timeString = date.toISOString().substr(11, 8);
        } else {
          timeString = "Infinite";
        }
        $(inputID).siblings("h3").find('.rangeSliderValue')[0].innerHTML = timeString;
      }
}

function get_osp_component_status(component) {
    console.log("Getting Status: " + component)
    socket.emit('admin_get_component_status', {component: component});
}

function get_all_osp_component_status() {
    get_osp_component_status('osp_core');
    get_osp_component_status('osp_rtmp');
    get_osp_component_status('osp_proxy');
    get_osp_component_status('osp_celery');
    get_osp_component_status('osp_ejabberd_chat');
    get_osp_component_status('osp_ejabberd_xmlrpc');
    get_osp_component_status('osp_database');
    get_osp_component_status('osp_redis');
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

function toggleHiddenRTMP(rtmpID) {
    socket.emit('toggleHideOSPRTMP', {rtmpID: rtmpID});
}

function deleteRTMP(rtmpID) {
    socket.emit('deleteOSPRTMP', {rtmpID: rtmpID});
    var rtmpTableRow = document.getElementById('rtmpTableRow-' + rtmpID);
    rtmpTableRow.parentNode.removeChild(rtmpTableRow);
}

function toggleActiveRTMP(rtmpID) {
    socket.emit('toggleOSPRTMP', {rtmpID: rtmpID});
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

function rebuildEdgeConf(){
    socket.emit('rebuildEdgeConf', {message: 'true'});
    createNewBSAlert("Config File Rebuilt.  Please restart the nginx-osp service on each OSP-Core server to take effect", "Success");
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

    if (webhookName === '') {
        (document.getElementById('webhookName')).setCustomValidity('Name is Required');
    }
    if (webhookEndpoint === '') {
        (document.getElementById('webhookEndpoint')).setCustomValidity('Endpoint URL is Required');
    }
    socket.emit('submitGlobalWebhook', {webhookName: webhookName, webhookEndpoint: webhookEndpoint, webhookHeader:webhookHeader, webhookPayload:webhookPayload, webhookReqType: webhookReqType, webhookTrigger: webhookTrigger, inputAction:webhookInputAction, webhookInputID:webhookInputID});

    if (webhookInputID !== null) {

        switch(webhookTrigger) {
          case '0':
            webhookTrigger = 'Stream Start';
            break;
          case '1':
            webhookTrigger = 'Stream End';
            break;
          case '2':
            webhookTrigger = 'Stream Viewer Join';
            break;
          case '3':
            webhookTrigger = 'Stream Viewer Upvote';
            break;
          case '4':
            webhookTrigger = 'Stream Name Change';
            break;
          case '5':
            webhookTrigger = 'Chat Message';
            break;
          case '6':
            webhookTrigger = 'New Video';
            break;
          case '7':
            webhookTrigger = 'Video Comment';
            break;
          case '8':
            webhookTrigger = 'Video Upvote';
            break;
          case '9':
            webhookTrigger = 'Video Name Change';
            break;
          case '10':
            webhookTrigger = 'Channel Subscription';
            break;
          case '20':
            webhookTrigger = 'New User';
            break;
        }
        document.getElementById('webhookRowName-' + webhookInputID).innerText = webhookName;
        document.getElementById('webhookRowEndpoint-' + webhookInputID).innerText = webhookEndpoint;
        document.getElementById('webhookRowHeader-' + webhookInputID).innerText = webhookHeader;
        document.getElementById('webhookRowPayload-' + webhookInputID).innerText = webhookPayload;
        document.getElementById('webhookRowType-' + webhookInputID).innerText = webhookReqType;
        document.getElementById('webhookRowTrigger-' + webhookInputID).innerText = webhookTrigger;
    }
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

function deleteStickerModal(stickerID) {
    document.getElementById('deleteStickerID').value = stickerID;
    $('#deleteStickerModal').modal('show');
}

function deleteSticker() {
    stickerID = document.getElementById('deleteStickerID').value;
    socket.emit('deleteSticker', {stickerID: stickerID});
    stickerDiv = document.getElementById('sticker-' + stickerID);
    stickerDiv.parentNode.removeChild(stickerDiv);
    document.getElementById('deleteStickerID').value = "";
    createNewBSAlert("Sticker Deleted","success")
}

function editStickerModal(stickerID) {
    stickerName = document.getElementById('sticker-name-' + stickerID).value;
    socket.emit('editSticker', {stickerID: stickerID, stickerName: stickerName});
    createNewBSAlert("Sticker Edited","success")
}

function disable2FAModal(userID) {
    var userIDInputDiv = document.getElementById('disable2FAUser');
    userIDInputDiv.value = userID;
    $('#disable2faModal').modal('show');
}

function disable2FA() {
    var userIDInputDiv = document.getElementById('disable2FAUser');
    var userID = userIDInputDiv.value;
    socket.emit('disable2FA', {userID: userID});
    var buttonSelector = document.getElementById('2fa-active-button-' + userID);
    buttonSelector.disabled = true;
}

function updateDefaultRoles() {
    var streamerChecked = document.getElementById("drole-streamer").checked;
    var recorderChecked = document.getElementById("drole-recorder").checked;
    var uploaderChecked = document.getElementById("drole-uploader").checked;
    socket.emit('updateDefaultRoles',{streamer: streamerChecked, recorder: recorderChecked, uploader: uploaderChecked});
}

function bulkAddRole(rolename) {
    var userIDArray = [];
    $("input:checkbox[name=selector-user]:checked").each(function(){
        userIDArray.push($(this).val());
    });

    socket.emit('bulkAddRoles',{users: userIDArray, role: rolename});
    window.location.replace("/settings/admin?page=users");
}

function deleteTopicModal(topicID) {
    document.getElementById('deleteTopicID').value = topicID;
    $('#deleteTopicModal').modal('show');
}

function deleteTopic() {
    topicID = document.getElementById('deleteTopicID').value;
    newTopic = document.getElementById('deleteNewTopicId').value;
    socket.emit('deleteTopic', {topicID: topicID, toTopicID: newTopic});
    topicDiv = document.getElementById('topic-' + topicID);
    topicDiv.parentNode.removeChild(topicDiv);
    document.getElementById('deleteTopicID').value = "";
    document.getElementById('deleteNewTopicId').value = "";
    createNewBSAlert("Topic Deleted","success")
}

function editTopicModal(topicID) {
    topicName = document.getElementById('topic-name-' + topicID).value;
    topicPhoto = document.getElementById('topic-pic-' + topicID).src;
    document.getElementById('newEditTopicName').value = topicName;
    document.getElementById('newEditTopicImg').src = topicPhoto;
    document.getElementById('existingTopicId').value = topicID;
    $('#newTopicModal').modal('show');
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

function editGlobalPanel(panelId) {
    document.getElementById('panel_modal_id').value = panelId;
    document.getElementById('panel_modal_name').value = document.getElementById('globalPanel-name-' + panelId).innerHTML;
    document.getElementById('panel_modal_header').value = document.getElementById('globalPanel-header-' + panelId).innerHTML;
    document.getElementById('panel_modal_type').value = document.getElementById('globalPanel-typeId-' + panelId).innerHTML;
    document.getElementById('panel_modal_order').value = document.getElementById('globalPanel-orderId-' + panelId).innerHTML;
    document.getElementById('panel_modal_content').value = document.getElementById('globalPanel-content-' + panelId).innerHTML;
    easymde_panel_editor.value = document.getElementById('globalPanel-content-' + panelId).innerHTML;
    var doc = easymde_panel_editor.codemirror.getDoc();
    doc.setValue(easymde_panel_editor.value);
    openModal('NewPanelModal');
}

function deleteGlobalPanelModal(panelId) {
    document.getElementById('globalPanelDeleteIDSelector').value = panelId;
    openModal('globalPanelDeleteModal')
}

function deleteGlobalPanel() {
    var globalPanelId = document.getElementById('globalPanelDeleteIDSelector').value;
    socket.emit('deleteGlobalPanel', {globalPanelId: globalPanelId});
    var panelDiv = document.getElementById('globalPanel-' + globalPanelId);
    panelDiv.parentNode.removeChild(panelDiv);
    document.getElementById('globalPanelDeleteIDSelector').value = "";
    var MappingElement = document.getElementById('front-panel-mapping-id-' + globalPanelId);
    MappingElement.parentNode.removeChild(MappingElement);
    createNewBSAlert("Global Panel Deleted","success")
}

function openFrontPageMappingModal() {
    document.getElementById('global_panel_front_page_mapping_add').value = '';
    openModal('globalPanelAddFrontPageModal');
}

function add_global_panel_mapping_to_front_page() {
    var globalPanelElem = document.getElementById('global_panel_front_page_mapping_add');
    var globalPanelId = globalPanelElem.value;
    var globalPanelText = globalPanelElem.options[globalPanelElem.selectedIndex].text;
    //socket.emit('add_global_panel_mapping_front_page',{'globalPanelId': globalPanelId});
    var panelMappingArrayElement = document.getElementById('panelOrderList');
    var newpanelMappingArrayElementLI = document.createElement('li');
    newpanelMappingArrayElementLI.setAttribute('id', 'front-panel-mapping-id-' + globalPanelId);
    newpanelMappingArrayElementLI.classList = 'd-flex align-items-center';
    newpanelMappingArrayElementLI.innerHTML = '<i class="fas fa-bars me-2"></i> ' + globalPanelText + '<span class="ms-auto me-2"><i class="fas fa-times" onClick="RemoveFrontPageLayoutPanel(this);"></i></span>';
    panelMappingArrayElement.appendChild(newpanelMappingArrayElementLI);
    createNewBSAlert("Global Panel Added to Front Page","success")
}

function save_global_panel_mapping_front_page() {
    var panelListItems = document.getElementById('panelOrderList').getElementsByTagName('li'),
    panelListArray = map(panelListItems, getNodeIds);
    socket.emit('save_global_panel_mapping_front_page', {globalPanelArray: panelListArray} )
    createNewBSAlert("Front Page Panel List Saved","success")
}

function setGlobalPanelTargetModal(panelId) {
    document.getElementById('globalPanelTargetChannelPanelId').value = panelId;
    document.getElementById('globalPanelTargetChannelOption').value = document.getElementById('globalPanel-target-' + panelId).innerHTML;
    openModal('globalPanelTargetChannelModal');
}

function setGlobalPanelTarget() {
    var panelId = document.getElementById('globalPanelTargetChannelPanelId').value;
    var targetId = document.getElementById('globalPanelTargetChannelOption').value;
    var channelNameElm = document.getElementById('globalPanelTargetChannelOption')
    var channelName = channelNameElm.options[channelNameElm.selectedIndex].text;
    socket.emit('setGlobalPanelTarget', {panelId: panelId, targetId: targetId});
    document.getElementById('globalPanel-targetName-' + panelId).innerHTML = channelName;
    document.getElementById('globalPanel-target-' + panelId).innerHTML = panelId
    createNewBSAlert('Panel Target Set', 'success')
}

function RemoveFrontPageLayoutPanel(callingElm) {
    var listElm = callingElm.parentElement.parentElement;
    listElm.parentNode.removeChild(listElm);
}

function openNewStaticPageModal() {
    document.getElementById('pageName').value = '';
    document.getElementById('pageIcon').value = '';
    document.getElementById('pageTitle').value = '';
    document.getElementById('pageContent').value = '';
    easymde_new_staticpage.codemirror.setValue('');
    document.getElementById('editPageId').value = '';
    openModal('NewStaticPageModal');
    easymde_new_staticpage.codemirror.refresh();
}

function saveStaticPage() {
    var formSection = document.getElementById('static_page_form');

    easymde_new_staticpage.codemirror.save();
    var pageNameDiv = document.getElementById('pageName');
    var pageIconDiv = document.getElementById('pageIcon');
    var pageTitleDiv = document.getElementById('pageTitle');
    var pageContentDiv = document.getElementById('pageContent');
    var existingPageId = document.getElementById('editPageId').value;
    var pageTopBarSelectDiv = document.getElementById('pageTopBarSelect');

    if (pageNameDiv.checkValidity() && pageIconDiv.checkValidity() && pageTitleDiv.checkValidity() && pageContentDiv.checkValidity()) {
        if ((existingPageId == null) || (existingPageId === '')) {
            socket.emit('addEditStaticPage', {
                pageName: pageNameDiv.value,
                pageIcon: pageIconDiv.value,
                pageContent: pageContentDiv.value,
                pageTitle: pageTitleDiv.value,
                pageTopBar: pageTopBarSelectDiv.checked,
                type: 'new'
            });
            createNewBSAlert('New Static Page Saved', 'Success');
        } else {
            socket.emit('addEditStaticPage', {
                pageName: pageNameDiv.value,
                pageIcon: pageIconDiv.value,
                pageContent: pageContentDiv.value,
                pageTitle: pageTitleDiv.value,
                pageTopBar: pageTopBarSelectDiv.checked,
                type: 'edit',
                pageId: existingPageId
            });

            document.getElementById('admin-staticpage-name-' + existingPageId).innerHTML = pageNameDiv.value;
            document.getElementById('admin-staticpage-icon-' + existingPageId).innerHTML = pageIconDiv.value;
            document.getElementById('admin-staticpage-title-' + existingPageId).innerHTML = pageTitleDiv.value;
            document.getElementById('admin-staticpage-content-' + existingPageId).innerHTML = pageContentDiv.value;
            document.getElementById('admin-staticpage-topbar-' + existingPageId).innerHTML = pageTopBarSelectDiv.checked.toString().charAt(0).toUpperCase() + pageTopBarSelectDiv.checked.toString().slice(1);
            document.getElementById('admin-staticpage-iconimg-' + existingPageId).classList = "textShadow " + pageIconDiv.value;

            createNewBSAlert('Static Page Updated', 'Success');
        }
        hideModal('NewStaticPageModal');
    } else {
        if (pageNameDiv.checkValidity() === false) {
            pageNameDiv.setCustomValidity('URL must contain only AlphaNumeric Characters without Spaces');
            pageNameDiv.reportValidity()
        }
        if (pageIconDiv.checkValidity() === false) {
            pageIconDiv.setCustomValidity('Field is Required');
            pageIconDiv.reportValidity()
        }
        if (pageTitleDiv.checkValidity() === false) {
            pageTitleDiv.setCustomValidity('Field is Required');
            pageTitleDiv.reportValidity()
        }
        if (pageContentDiv.checkValidity() === false) {
            pageContentDiv.setCustomValidity('Field is Required');
            pageContentDiv.reportValidity()
        }
    }
}

function editStaticPage(pageId) {
    var pageNameDiv = document.getElementById('pageName');
    var pageIconDiv = document.getElementById('pageIcon');
    var pageTitleDiv = document.getElementById('pageTitle');
    var pageContentDiv = document.getElementById('pageContent');
    var pageTopBarDiv = document.getElementById('pageTopBarSelect');

    var data_pageName = document.getElementById('admin-staticpage-name-' + pageId).innerHTML;
    var data_pageIcon = document.getElementById('admin-staticpage-icon-' + pageId).innerHTML;
    var data_pageTitle = document.getElementById('admin-staticpage-title-' + pageId).innerHTML;
    var data_pageContent = document.getElementById('admin-staticpage-content-' + pageId).innerHTML;

    if (document.getElementById('admin-staticpage-topbar-' + pageId).innerHTML === 'true' || document.getElementById('admin-staticpage-topbar-' + pageId).innerHTML === 'True' ) {
        pageTopBarDiv.checked = true;
    } else {
        pageTopBarDiv.checked = false;
    }

    pageNameDiv.value = data_pageName;
    pageIconDiv.value = data_pageIcon;
    pageTitleDiv.value = data_pageTitle;
    easymde_new_staticpage.codemirror.setValue(data_pageContent);

    easymde_new_staticpage.codemirror.refresh();

    document.getElementById('editPageId').value = pageId;

    openModal('NewStaticPageModal');
}

function deleteStaticPageModal(pageId) {
    document.getElementById('deleteStaticPageId').value = pageId;
    openModal('deleteStaticPageModal');
}

function deleteStaticPage() {
    var pageId = document.getElementById('deleteStaticPageId').value;
    var pageTableDiv = document.getElementById('admin-staticpage-' + pageId);
    pageTableDiv.parentNode.removeChild(pageTableDiv);
    socket.emit('deleteStaticPage', {pageId: pageId});
    createNewBSAlert('Static Page Deleted', 'Success');
    document.getElementById('deleteStaticPageId').value = '';
}

function call_celery_task(taskname) {
    socket.emit('call_celery_task',{task: taskname});
    createNewBSAlert('Task Request Sent', 'success');
}

function deleteOAuthProvider(providerID) {
    document.getElementById('DeleteOAuthProviderID').value = providerID;
}

function transferChannelModal(channelID) {
    document.getElementById('transferChannelId').value = channelID;
    document.getElementById('channelTransferUsernameSelect').value = '';
    openModal('transferChannelModal');
}

function transferChannel() {
    sel = document.getElementById('channelTransferUsernameSelect')
    channelId = document.getElementById('transferChannelId').value;
    newOwner = sel.value;
    socket.emit('transferChannelOwner', {channelId: channelId, userId: newOwner});

    updatedUserName = sel.options[sel.selectedIndex].text;
    updatedEntry = document.getElementById('channelCardRow-' + channelId + '-userCol');
    updatedEntry.innerHTML = '<a href="/profile/' + updatedUserName + '">' + updatedUserName + '</a>'
    createNewBSAlert('Channel Transfered to New Owner...', 'success')
}