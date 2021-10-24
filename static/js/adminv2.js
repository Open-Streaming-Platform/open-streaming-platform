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
    socket.emit('admin_get_component_status', {component: component});
}

function get_all_osp_component_status() {
    get_osp_component_status('osp_core');
    get_osp_component_status('osp_rtmp');
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