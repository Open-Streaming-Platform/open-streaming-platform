var inputElm = document.querySelector('input[name=toUsersList]');
var controller = new AbortController();

function tagTemplate(tagData){
    return `
        <tag title="${tagData.email}"
                contenteditable='false'
                spellcheck='false'
                tabIndex="-1"
                class="tagify__tag ${tagData.class ? tagData.class : ""}"
                ${this.getAttributes(tagData)}>
            <x title='' class='tagify__tag__removeBtn' role='button' aria-label='remove tag'></x>
            <div>
                <div class='tagify__tag__avatar-wrap'>
                    <img onerror="this.style.visibility='hidden'" src="${tagData.avatar}">
                </div>
                <span class='tagify__tag-text'>${tagData.name}</span>
            </div>
        </tag>
    `
}

function suggestionItemTemplate(tagData){
    return `
        <div ${this.getAttributes(tagData)}
            class='tagify__dropdown__item ${tagData.class ? tagData.class : ""}'
            tabindex="0"
            role="option">
            ${ tagData.avatar ? `
            <div class='tagify__dropdown__item__avatar-wrap'>
                <img onerror="this.style.visibility='hidden'" src="${tagData.avatar}">
            </div>` : ''
            }
            <strong>${tagData.name}</strong>
        </div>
    `
}
/////////////////////////////////////////////////////////////////
// Message To Input Handler
/////////////////////////////////////////////////////////////////

// initialize Tagify on the above input node reference
var input = inputElm;
messageToTaggify = new Tagify(input, {
    tagTextProp: 'name', // very important since a custom template is used with this property as text
    enforceWhitelist: true,
    skipInvalid: true, // do not remporarily add invalid tags
    dropdown: {
        closeOnSelect: false,
        enabled: 0,
        classname: 'users-list',
        searchKeys: ['name']  // very important to set by which keys to search for suggesttions when typing
    },
    templates: {
        tag: tagTemplate,
        dropdownItem: suggestionItemTemplate
    },
    whitelist: [],
    controller
})

// listen to any keystrokes which modify tagify's input
messageToTaggify.on('input', function(e) {
    var value = e.detail.value
    messageToTaggify.whitelist = null // reset the whitelist

    // https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort
    controller && controller.abort()
    controller = new AbortController()

   // show loading animation and hide the suggestions dropdown
    messageToTaggify.loading(true).dropdown.hide()

    $.post('/apiv1/user/search', {term: value}, function (RES) {
        var newWhitelist = RES['results'];
        resultWhitelist = []
        for (var i = 0; i < newWhitelist.length; i++) {
            var entry = newWhitelist[i];
            resultWhitelist.push(
                {
                    value: entry[0],
                    name: entry[1],
                    email: '',
                    avatar: '/images/' + entry[3]
                }
                )
        }
        messageToTaggify.whitelist = resultWhitelist // update whitelist Array in-place
        messageToTaggify.loading(false).dropdown.show(value) // render the suggestions dropdown
        })
});

var addAllSuggestionsElm;
messageToTaggify.on('dropdown:show dropdown:updated', function(e) {
    var dropdownContentElm = e.detail.tagify.DOM.dropdown.content;

    if( messageToTaggify.suggestedListItems.length > 1 ){
        addAllSuggestionsElm = function(){
                // suggestions items should be based on "dropdownItem" template
            return messageToTaggify.parseTemplate('dropdownItem', [{
                class: "addAll",
                name: "Add all",
                email: messageToTaggify.whitelist.reduce(function(remainingSuggestions, item){
                    return messageToTaggify.isTagDuplicate(item.value) ? remainingSuggestions : remainingSuggestions + 1
                }, 0) + " Members"
            }]
            )};

        // insert "addAllSuggestionsElm" as the first element in the suggestions list
        dropdownContentElm.insertBefore(addAllSuggestionsElm, dropdownContentElm.firstChild)
    }
})

messageToTaggify.on('dropdown:select', function(e){
    if( e.detail.elm === addAllSuggestionsElm )
    messageToTaggify.dropdown.selectAll();
})


/////////////////////////////////////////////////////////////////
// Ban List Names
/////////////////////////////////////////////////////////////////


/////////////////////////////////////////////////////////////////

function getAllCheckedMessages() {
    var messageIdArray = [];
    var checkboxes = document.getElementsByName('messageList-checkbox');
    for (var checkbox of checkboxes)
    {
        if (checkbox.checked) {
            messageIdArray.push(checkbox.value);
        }
    }
    return messageIdArray;
}

function toggleAllMessages() {
    var allChecks = document.getElementById('selectAllCheckbox').checked;
    var checkboxes = document.getElementsByName('messageList-checkbox');
    for (var checkbox of checkboxes)
    {
        checkbox.checked = allChecks;
    }

    if (allChecks === true) {
        $('#selectedMessages').show();
    } else {
        $('#selectedMessages').hide();
    }
}

$(document).ready(function(){
    $('input[name="messageList-checkbox"]').click(function(){
        if ($('input[name="messageList-checkbox"]:checked').length > 0) {
            $('#selectedMessages').show();
        } else {
            $('#selectedMessages').hide();
        }
    });
});

function markCheckedMessageAsRead() {
    var messagesArrayList = getAllCheckedMessages();
    socket.emit('markMessageRead', {messageId: messagesArrayList});
    for (var i = 0; i < messagesArrayList.length; i++) {
        document.getElementById('message-subject-' + messagesArrayList[i]).classList.remove('bold');
    }
}

function markAllMessagesAsRead() {
    var checkboxes = document.getElementsByName('messageList-checkbox');
    for (var checkbox of checkboxes)
    {
        checkbox.checked = true;
    }
    markCheckedMessageAsRead()
    for (var checkbox of checkboxes)
    {
        checkbox.checked = false;
    }
}

function openNewMessageModal() {
    document.getElementById('toUsersList').value = '';
    document.getElementById('messageSubject').value = '';
    document.getElementById('messageContent').value = '';
    easymde_new_message.value = '';
    var doc = easymde_new_message.codemirror.getDoc();
    doc.setValue(easymde_new_message.value);
    easymde_new_message.codemirror.refresh();
    openModal('newMessageModal')
}

function sendMessage() {
    var sendMessageTo = JSON.parse(document.getElementById('toUsersList').value);
    var messageSubject = document.getElementById('messageSubject').value;
    var messageContent = easymde_new_message.codemirror.getDoc().getValue();

    if ((sendMessageTo === '') || (messageSubject.trim() === '') || (messageContent.trim === '')) {
    createNewBSAlert('Message Not Sent.  Required Fields Were Empty', 'error');
    } else {
        socket.emit('sendMessage', {
            sendMessageTo: sendMessageTo,
            messageSubject: messageSubject,
            messageContent: messageContent
        });
        createNewBSAlert('Message Queued', 'success');
    }
}

function deleteSelectedMessage() {
    var messagesArrayList = getAllCheckedMessages();
    socket.emit('deleteMessage', {messageId: messagesArrayList});
    for (var i = 0; i < messagesArrayList.length; i++) {
        var messageListRow = document.getElementById('message-' + messagesArrayList[i]);
        messageListRow.parentNode.removeChild(messageListRow);
    }
    $('#message').hide();
    $('#messages-view-control').hide();
}

function deleteActiveMessage() {
    var messageId = document.getElementById('active-messageId').value;
    socket.emit('deleteMessage', {messageId: [messageId]});
    var messageListRow = document.getElementById('message-' + messageId);
    messageListRow.parentNode.removeChild(messageListRow);
    $('#message').hide();
    $('#messages-view-control').hide();

}

function getMessage(messageID) {
    $('#message-loading').show();
    socket.emit('getMessage', {messageID: messageID});
    document.getElementById('message-subject-' + messageID).classList.remove('bold');
}

socket.on('returnMessage', function (msg) {
    $('#message-loading').hide();
    $('#message').show();
    document.getElementById('message-content').innerHTML = msg['content'];
    document.getElementById('message-subject').innerHTML = msg['subject'];
    document.getElementById('message-timestamp').innerHTML = msg['timestamp'];
    document.getElementById('message-from-img').src = '/images/' + msg['fromUserPhoto'];
    document.getElementById('message-from-username').innerHTML = msg['fromUsername'];
    document.getElementById('message-from-id').innerHTML = msg['fromUser'];
    document.getElementById('active-messageId').value = msg['id'];
    $('#messages-view-control').show();
});

function replyMessage() {
    var fromUser = document.getElementById('message-from-username').innerHTML
    $.post('/apiv1/user/search', {term: fromUser}, function (RES) {
        var newWhitelist = RES['results'];
        resultWhitelist = []
        for (var i = 0; i < newWhitelist.length; i++) {
            var entry = newWhitelist[i];
            resultWhitelist.push(
                {
                    value: entry[0],
                    name: entry[1],
                    email: '',
                    avatar: '/images/' + entry[3]
                }
            )
        }
        messageToTaggify.whitelist = resultWhitelist // update whitelist Array in-place
        messageToTaggify.addTags(fromUser);
    });
    easymde_new_message.value = '';
    var doc = easymde_new_message.codemirror.getDoc();
    doc.setValue(easymde_new_message.value);
    easymde_new_message.codemirror.refresh();
    document.getElementById('messageSubject').value = "RE: " + document.getElementById('message-subject').innerHTML;
    openModal('newMessageModal');
}