function clearListNotification(notificationID) {
    var listEntry = document.getElementById('notificationList-' + notificationID);
    listEntry.parentNode.removeChild(listEntry);
    clearNotification(notificationID);
    if (notificationCount <= 0) {
        emptyNotificationList.style.display = "block";
    }
}

function clearAllListNotifications() {
  var ids = $('.notificationBodyFull .notification-box').map(function(){
    return $(this).attr('id');
    }).get();
  ids.forEach(function (item, index) {
    if (item != 'notificationList-empty') {
      item = item.replace('notificationList-','');
      clearNotification(item);
    }
  });
  if (notificationCount <= 0) {
    emptyNotificationList.style.display = "block";
  }
}

function clearNotification(notificationID) {
  var notification = document.getElementById('notification-' + notificationID);
  notification.parentNode.removeChild(notification);

  var newCount = notificationCount - 1;
  if (newCount <= 0) {
    var emptyNotificationBar = document.getElementById("notification-empty");

    notificationCountMobile.style.display = "none";
    notificationCountNav.style.display = "none";
    emptyNotificationBar.style.display = "block";
    newCount = 0;
  }

  notificationCountMobile.innerText = newCount;
  notificationCountNav.innerText = newCount;
  notificationCountMenu.innerText = newCount;
  notificationCount = notificationCount - 1;

  socket.emit('markNotificationAsRead', { data: notificationID });
}