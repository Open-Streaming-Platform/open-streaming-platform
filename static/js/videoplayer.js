// Socket.IO Connection
var conn_options = {'sync disconnect on unload':true};
var socket = io();

var easymdeVideoEditor = new EasyMDE({ autoDownloadFontAwesome: false, spellChecker: false, element: document.getElementById("description")});

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

function secondsToTimeHMS(seconds) {
    var secondString = (seconds % 60).toString().padStart(2,'0');
    if (seconds < 60) {
        return `0:00:${secondString}`;
    }

    var minuteString = (Math.floor(seconds / 60) % 60).toString().padStart(2,'0');
    if (seconds < 3600) {
        return `0:${minuteString}:${secondString}`;
    }

    var hourString = Math.floor(seconds / 3600).toString();
    return `${hourString}:${minuteString}:${secondString}`;
}

function changeUpvote(type, id) {
    socket.emit('changeUpvote', {loc: id, vidType: type});
}

function toggleChannelSub(chanID) {
    socket.emit('toggleChannelSubscription', { channelID: chanID });
}

socket.on('checkScreenShot', function (msg) {
    console.log('Received New Thumbnail');
    document.getElementById('screenshotPendingBox').style.display = "none";
    document.getElementById('screenshotImageBox').style.display = "block";
    document.getElementById("newScreenShotImg").src = msg['thumbnailLocation'];
    document.getElementById('newScreenShotSetThumbButton').disabled = false;
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
    document.getElementById('screenshotPendingBox').style.display = "block";
    document.getElementById('screenshotImageBox').style.display = "none";
    document.getElementById('newScreenShotSetThumbButton').disabled = true;
    openModal('newSSModal');
}

function setNewThumbnail() {
    var timestamp = document.getElementById("thumbnailTimestamp").value;
    socket.emit('setScreenShot', { loc: videoID, timeStamp: timestamp });
    createNewBSAlert("New Thumbnail Set", "success")
    document.getElementById('screenshotPendingBox').style.display = "block";
    document.getElementById('screenshotImageBox').style.display = "none";
    document.getElementById('newScreenShotSetThumbButton').disabled = true;
}


function openClipModal() {
    player.pause();
    var playerCurrentTime = player.currentTime();
    clipplayer.currentTime(playerCurrentTime);

    var startInput = document.getElementById('clipStartTime');
    startInput.value = null;

    var stopInput = document.getElementById('clipStopTime');
    stopInput.value = null;

    var clipDescriptionInput = document.getElementById('clipDescription');
    clipDescriptionInput.value = null;

    var clipCurrentLengthSpan = document.getElementById('clipCurrentLength');
    clipCurrentLengthSpan.innerText = null;

    var clipErrorDiv = document.getElementById('clipError');
    clipErrorDiv.innerHTML = "";
    clipErrorDiv.style.display = "none";

    var clipMaxLengthSpan = document.getElementById('clipMaxLength');
    if (maxClipLength > 300) {
      clipMaxLengthSpan.innerText = 'Infinite';
    } else {
      clipMaxLengthSpan.innerText = secondsToTimeHMS(maxClipLength);
    }

    $("#clipModal").modal('show');
}

function clipStartGoTo() {
    var startInputValue = parseInt(document.getElementById('clipStartTime').value);
    if (isNaN(startInputValue)) return;
    clipplayer.currentTime(startInputValue);
}

function clipStopGoTo() {
    var stopInputValue = parseInt(document.getElementById('clipStopTime').value);
    if (isNaN(stopInputValue)) return;
    clipplayer.currentTime(stopInputValue);
}

function setClipStart() {
    var startInput = document.getElementById('clipStartTime');
    startInput.value = parseInt(clipplayer.currentTime());
    checkClipConstraints();
}

function setClipStop() {
    var stopInput = document.getElementById('clipStopTime');
    stopInput.value = parseInt(clipplayer.currentTime());
    checkClipConstraints();
}

function checkClipConstraints() {
    var startTime = parseInt(document.getElementById('clipStartTime').value);
    var stopTime = parseInt(document.getElementById('clipStopTime').value);
    var systemMaxClipLength = maxClipLength;
    var clipErrorDiv = document.getElementById('clipError');
    var clipSubmitButton = document.getElementById('clipSubmitButton');

    var clipCurrentLengthSpan = document.getElementById('clipCurrentLength');

    if (isNaN(startTime) || isNaN(stopTime)) {
        clipErrorDiv.innerHTML = "";
        clipErrorDiv.style.display = "none";
        clipSubmitButton.disabled = true;
        clipCurrentLengthSpan.innerText = '';
        return;
    }

    try {
        if (startTime >= stopTime) {
            clipCurrentLengthSpan.innerText = '';
            throw new Error("Start Time must be less than End Time");
        }

        var clipLength = stopTime - startTime;
        clipCurrentLengthSpan.innerText = secondsToTimeHMS(clipLength);
        if (systemMaxClipLength < 301) {
            if (clipLength > systemMaxClipLength) {
                throw new Error(`Clip is longer than the maximum allowed length of ${secondsToTimeHMS(systemMaxClipLength)}!`);
            }
        }

        clipErrorDiv.innerHTML = "";
        clipErrorDiv.style.display = "none";
        clipSubmitButton.disabled = false;
    } catch (err) {
        clipErrorDiv.innerHTML = err.message;
        clipErrorDiv.style.display = "block";
        clipSubmitButton.disabled = true;
    }
}

function createClip() {
    clipplayer.pause();
    var videoID = document.getElementById('clipvideoID').value;
    var clipName = document.getElementById('clipName').value;
    var clipDescription = document.getElementById('clipDescription').value;
    var clipStart = document.getElementById('clipStartTime').value;
    var clipStop = document.getElementById('clipStopTime').value;

    socket.emit('createClip', {videoID: videoID, clipName: clipName, clipDescription: clipDescription, clipStart: clipStart, clipStop:clipStop});
    createNewBSAlert("Clip Queued for Creation", "Success");
}

function hideComments() {
    var commentsDiv = document.getElementById('commentsPanel');
    var contentsDiv = document.getElementById('mainContentPanel');
    commentsDiv.style.display = 'none';
    contentsDiv.className = 'col-9 mx-auto';
}

function confirmDeleteComment(commentId) {
    document.getElementById('deleteCommentId').value = commentId;
    openModal('confirmDeleteCommentModal');
}

function deleteComment(){
    var commentId = document.getElementById('deleteCommentId').value;
    document.getElementById('deleteCommentId').value = '';
    socket.emit('deleteVideoComment', {commentID: commentId});
    var commentDiv = document.getElementById('vidComment-' + commentId);
    commentDiv.parentElement.removeChild(commentDiv);
}
