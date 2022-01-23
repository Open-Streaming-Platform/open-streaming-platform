function updateSocialInputIcon() {
    var changeValElm = document.getElementById('socialNetworkType');
    var changeVal = changeValElm.options[changeValElm.selectedIndex].value;
    document.getElementById('socialIconInput').src = '/static/img/socialnetwork/social-' + changeVal + '.png'
}

function addSocialNetwork() {
    var changeValElm = document.getElementById('socialNetworkType');

    socket.emit('addSocialNetwork', {socialType: changeValElm.options[changeValElm.selectedIndex].value, url: document.getElementById('socialNetworkURL').value});

    changeValElm.selectedIndex = 0;
    document.getElementById('socialNetworkURL').value = '';

    updateSocialInputIcon();

}

function deleteSocialNetwork(id) {
    socket.emit('removeSocialNetwork', {id: id});
    var elm = document.getElementById('socialNetwork-' + id);
    elm.parentElement.removeChild(elm);
}

socket.on('returnSocialNetwork', function (msg) {
    var socialNetworkTable = document.getElementById('socialNetworkTable');

    var returnID = msg['id']
    var socialType = msg['socialType']
    var url = msg['url']

    var row = socialNetworkTable.insertRow(socialNetworkTable.rows.length-1);
    row.id = 'socialNetwork-' + returnID;
    row.classList = 'align-middle';

    var cell1 = row.insertCell(0);
    var cell2 = row.insertCell(1);
    var cell3 = row.insertCell(2);
    var cell4 = row.insertCell(3);

    cell1.innerHTML = '<img class="socialIcon boxShadow" src="/static/img/socialnetwork/social-' + socialType + '.png">'
    cell2.innerHTML = socialType;
    cell3.innerHTML = url;
    cell4.innerHTML = '<button class="btn btn-sm btn-danger" onclick="deleteSocialNetwork(' + returnID + ');"><i class="fas fa-trash-alt"></i></button>'
});
