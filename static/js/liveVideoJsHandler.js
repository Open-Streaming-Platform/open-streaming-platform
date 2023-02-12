//Fixes for VideoJS on Disconnect to Force a Reconnect when the readyState is stuck at 2 or when a live stream starts after having been offline
function monitor_vid(vidplayer){

    videoJSObj = vidplayer;
    currentReadyState = videoJSObj.readyState();

    videoWindowState = document.getElementsByTagName('video');

    videoContainer = document.getElementById('videoContainer');
    offlineWindow = document.getElementById('offlineImage');

    onlineBadge = document.getElementById('liveIndicatorBadge');

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

            var currentStreamTopic = currentStream['topic'];
            var currentStreamName = currentStream['streamName'];
            streamTimeStamp = new Date(currentStream['startTimestamp'] + ' UTC');

            var topicDiv = document.getElementById('streamMetadataTopic');
            var nameDiv = document.getElementById('streamMetadataName');

            var nameDivHTML = '<b><i class="fas fa-video"></i> <span> ' + currentStreamName +  '</span></b>';
            var topicDivHTML = '<b><i class="fas fa-hashtag"></i> <a href="/topics/' + currentStreamTopic + '"><span>' + topicJSList[currentStreamTopic] +  '</span></a></b>';

            onlineBadge.className = 'btn btn-danger boxShadow';
            onlineBadge.innerHTML = 'LIVE';

            nameDiv.innerHTML = nameDivHTML;
            topicDiv.innerHTML = topicDivHTML;


        } else {
            try {
                videoJSObj.pause();
                videoJSObj.reset();
                onlineBadge.className = 'btn btn-secondary boxShadow';
                onlineBadge.innerHTML = 'OFFLINE';
                videoContainer.style.display = "none";
                offlineWindow.style.display = "block";
                var currentStreamName = "No Stream";
                var nameDiv = document.getElementById('streamMetadataName');
                streamTimeStamp = new Date('UTC');
                var nameDivHTML = '<span><b> ' + currentStreamName +  '</b></span>';
                nameDiv.innerHTML = nameDivHTML;
                disableTheaterMode();

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
var monitorInterval = setInterval(function() {
    monitor_vid(player);
}, 10000);

const videoElm = document.querySelector('video');
videoElm.addEventListener('play', (event) => {
    var cookieVolume = getCookie('ospvolume');
    if (!(cookieVolume == null)) {
      player.volume(cookieVolume);
    }
});

videoElm.addEventListener('volumechange', (event) => {
    var currentVolume = player.volume();
    setCookie('ospvolume',currentVolume, 365);
});