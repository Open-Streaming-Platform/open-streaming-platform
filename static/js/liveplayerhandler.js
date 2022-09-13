

function changeUpvote() {
    socket.emit('changeUpvote', {loc: channelLocation, vidType: 'stream'});
}

function toggleChat() {
    var chatbox = document.getElementById("chatPanel");
    if (chatbox.style.display === "none") {
        chatbox.style.display = "block";
    } else {
        chatbox.style.display = "none";
    }
}

socket.on('sendChanSubResults', function (msg) {
    var subButton = document.getElementById('chanSubStateButton');
    if (msg['state'] === true) {
        subButton.innerHTML = "<i class='fas fa-star'></i><span class='d-none d-sm-none d-md-inline'> Unsubscribe</span>";
        subButton.className = "btn btn-success";
    } else {
        subButton.innerHTML = "<i class='far fa-star'></i><span class='d-none d-sm-none d-md-inline'> Subscribe</span>";
        subButton.className = "btn btn-outline-success";
    }
});

socket.on('upvoteTotalResponse', function (msg) {
    document.getElementById("totalUpvotes").innerHTML = msg['totalUpvotes'];
    if (msg['myUpvote'] === 'True'){
        if ( document.getElementById("upVoteIcon").classList.contains('far') ) {
            document.getElementById("upVoteIcon").classList.remove('far');
            document.getElementById("upVoteIcon").classList.add('fas');
        }
    }
    else if (msg['myUpvote'] === 'False'){
        if ( document.getElementById("upVoteIcon").classList.contains('fas') ) {
            document.getElementById("upVoteIcon").classList.remove('fas');
            document.getElementById("upVoteIcon").classList.add('far');
        }
    }
});

socket.on('connect', function() {
    socket.emit('getUpvoteTotal', {loc: channelLocation, vidType: 'stream'});
    socket.emit('getViewerTotal', {data: channelLocation} );
});

setInterval(function() {
  socket.emit('getUpvoteTotal', {loc: channelLocation, vidType: 'stream'});
},30000 );

setInterval(function() {
  socket.emit('getViewerTotal', {data: channelLocation} );
},10000 );


const videoElm = document.querySelector('video');
videoElm.addEventListener('play', (event) => {
    var cookieVolume = getCookie('ospvolume');
    if (!(cookieVolume == null)) {
      player.setVolume(cookieVolume);
    }
});

videoElm.addEventListener('volumechange', (event) => {
    var currentVolume = player.getVolume();
    setCookie('ospvolume',currentVolume, 365);
});
