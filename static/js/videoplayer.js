// Socket.IO Connection
var conn_options = {'sync disconnect on unload':true};
var socket = io();

socket.on('connect', function () {
    console.log('Connected to SocketIO');
    socket.emit('getUpvoteTotal', {loc: videoID, vidType: 'video'});
});

setInterval(function () {
    socket.emit('getUpvoteTotal', {loc: videoID, vidType: 'video'});
}, 30000);

socket.on('upvoteTotalResponse', function (msg) {
    if (msg['type'] === 'video') {
        upvoteDivID = 'totalUpvotes';
        upvoteIconID = 'upVoteIcon';
        upvoteButtonID = 'upvoteButton';
    } else if (msg['type'] === 'comment') {
        upvoteDivID = 'upvoteTotalComments-' + msg['loc'];
        upvoteIconID = 'commentUpvoteIcon-' + msg['loc'];
        upvoteButtonID = 'commentUpvoteButton-' + msg['loc'];
    }

    document.getElementById(upvoteDivID).innerHTML = msg['totalUpvotes'];

    if (msg['myUpvote'] === 'True') {
        if (document.getElementById(upvoteIconID).classList.contains('far')) {
            document.getElementById(upvoteIconID).classList.remove('far');
            document.getElementById(upvoteIconID).classList.add('fas');
        }
        if (document.getElementById(upvoteButtonID).classList.contains('btn-outline-success')) {
            document.getElementById(upvoteButtonID).classList.remove('btn-outline-success');
            document.getElementById(upvoteButtonID).classList.add('btn-success');
        }
    } else if (msg['myUpvote'] === 'False') {
        if (document.getElementById(upvoteIconID).classList.contains('fas')) {
            document.getElementById(upvoteIconID).classList.remove('fas');
            document.getElementById(upvoteIconID).classList.add('far');
        }
        if (document.getElementById(upvoteButtonID).classList.contains('btn-success')) {
            document.getElementById(upvoteButtonID).classList.remove('btn-success');
            document.getElementById(upvoteButtonID).classList.add('btn-outline-success');
        }
    }
});

socket.on('sendChanSubResults', function (msg) {
    var subButton = document.getElementById('chanSubStateButton');
    if (msg['state'] === true) {
        subButton.innerHTML = "<i class='fas fa-star'></i><span class='d-none d-sm-none d-md-inline'> Unsubscribe</span>";
        subButton.className = "btn boxshadow btn-success";
    } else {
        subButton.innerHTML = "<i class='far fa-star'></i><span class='d-none d-sm-none d-md-inline'> Subscribe</span>";
        subButton.className = "btn boxshadow btn-outline-success";
    }
});

function changeUpvote(type, id) {
    socket.emit('changeUpvote', {loc: id, vidType: type});
}

function toggleChannelSub(chanID) {
    socket.emit('toggleChannelSubscription', { channelID: chanID });
}

socket.on('checkScreenShot', function (msg) {
    document.getElementById("newScreenShotImg").src = msg['thumbnailLocation'];
    openModal('newSSModal')
});

function toggleShareTimestamp(requestURL, startTime) {
    if (document.getElementById('shareTimestamp').checked)
    {
        document.getElementById('embedURLInput').value = '<iframe src="' + requestURL + '?embedded=True&autoplay=True&startTime='.replace('?startTime=' + startTime,'') + player.currentTime() + '" width=600 height=345></iframe>';
        document.getElementById('linkShareInput').value = requestURL.replace('?startTime=' + startTime,'') + '?startTime=' + player.currentTime();
    } else {
        document.getElementById('embedURLInput').value = '<iframe src="' + requestURL + '?embedded=True&autoplay=True" width=600 height=345></iframe>'.replace('?startTime=' + startTime,'');
        document.getElementById('linkShareInput').value = requestURL.replace('?startTime=' + startTime,'');
    }
}

function newThumbnailRequest() {
    player.pause();
    window.whereYouAt = player.currentTime();
    document.getElementById("thumbnailTimestamp").value = window.whereYouAt;
    socket.emit('newScreenShot', { loc: videoID, timeStamp: window.whereYouAt });
}

function setNewThumbnail() {
    var timestamp = document.getElementById("thumbnailTimestamp").value;
    socket.emit('setScreenShot', { loc: videoID, timeStamp: timestamp });
    createNewBSAlert("New Thumbnail Set", "success")
}


function openClipModal() {
    player.pause();

    var startInput = document.getElementById('clipStartTime');
    startInput.value = null;

    var stopInput = document.getElementById('clipStopTime');
    stopInput.value = null;

    var clipDescriptionInput = document.getElementById('clipDescription');
    clipDescriptionInput.value = null;
    $("#clipModal").modal('show');
}

function setClipStart() {
    var startInput = document.getElementById('clipStartTime');
    startInput.value = clipplayer.currentTime()
    checkClipConstraints();
}

function setClipStop() {
    var stopInput = document.getElementById('clipStopTime');
    stopInput.value = clipplayer.currentTime()
    checkClipConstraints();
}

function checkClipConstraints() {
    var startTime = document.getElementById('clipStartTime').value;
    var stopTime = document.getElementById('clipStopTime').value;
    var systemMaxClipLength = maxClipLength;
    var clipErrorDiv = document.getElementById('clipError');
    var clipSubmitButton = document.getElementById('clipSubmitButton');

    if (systemMaxClipLength < 301) {
          if ((startTime !== "") && (stopTime !== "")) {
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

function createClip() {
    var videoID = document.getElementById('clipvideoID').value;
    var clipName = document.getElementById('clipName').value;
    var clipDescription = document.getElementById('clipDescription').value;
    var clipStart = document.getElementById('clipStartTime').value;
    var clipStop = document.getElementById('clipStopTime').value;

    socket.emit('createClip', {videoID: videoID, clipName: clipName, clipDescription: clipDescription, clipStart: clipStart, clipStop:clipStop});
    createNewBSAlert("Clip Queued for Creation", "Success");
}
