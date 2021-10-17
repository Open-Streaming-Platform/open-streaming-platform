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