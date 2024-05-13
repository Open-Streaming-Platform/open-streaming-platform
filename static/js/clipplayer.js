// Socket.IO Connection
var conn_options = {'sync disconnect on unload':true};
var socket = io();

var easymdeClipEditor = new EasyMDE({ autoDownloadFontAwesome: false, spellChecker: false, element: document.getElementById("description")});

socket.on('connect', function () {
    console.log('Connected to SocketIO');
    socket.emit('getUpvoteTotal', {loc: clipID, vidType: 'clip'});
});

setInterval(function () {
    socket.emit('getUpvoteTotal', {loc: clipID, vidType: 'clip'});
}, 30000);

socket.on('upvoteTotalResponse', function (msg) {
    if (msg['type'] === 'clip') {
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
    socket.emit('changeUpvote', {loc: id, vidType: 'clip'});
}

function toggleChannelSub(chanID) {
    socket.emit('toggleChannelSubscription', { channelID: chanID });
}

socket.on('checkClipScreenShot', function (msg) {
    document.getElementById("newScreenShotImg").src = msg['thumbnailLocation'];
    document.getElementById('screenshotPendingBox').style.display = "none";
    document.getElementById('screenshotImageBox').style.display = "block";
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
    document.getElementById('newScreenShotSetThumbButton').disabled = true;
    document.getElementById('screenshotPendingBox').style.display = "block";
    document.getElementById('screenshotImageBox').style.display = "none";
    document.getElementById("thumbnailTimestamp").value = window.whereYouAt;
    openModal('newSSModal')
    socket.emit('newScreenShot', { loc: null, timeStamp: window.whereYouAt, clipID: clipID, clip:true });
}

function setNewThumbnail() {
    var timestamp = document.getElementById("thumbnailTimestamp").value;
    socket.emit('setScreenShot', { clipID: clipID, timeStamp: timestamp });
    createNewBSAlert("New Thumbnail Set", "success")
}

function hideComments() {
    var commentsDiv = document.getElementById('commentsPanel');
    var contentsDiv = document.getElementById('mainContentPanel');
    commentsDiv.style.display = 'none';
    contentsDiv.className = 'col-9 mx-auto';
}
