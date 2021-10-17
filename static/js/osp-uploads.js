
function s4() {
  return Math.floor((1 + Math.random()) * 0x10000)
    .toString(16)
    .substring(1);
}

videofilename = s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();

// Used for Video Upload Cancel Cleanup
function videouploadsocket() {
  var conn_options = {
    'sync disconnect on unload': true
  };
  var socket = io();

  socket.on('disconnect', function () {
    socket.emit('cancelUpload', { data: videofilename });
  });
  window.addEventListener("beforeunload", function (e) {
    socket.emit('cancelUpload', { data: videofilename });
    return null;
  });
}

// Thumbnail Uploads
var thumbnaildropper = new Dropzone(
  '#thumbnaildropper', {
  acceptedFiles: 'image/png',
  previewTemplate: '<div></div>',
  clickable: '#thumbnailuploadbutton',
  addRemoveLinks: true,
  paramName: 'file',
  chunking: true,
  forceChunking: true,
  url: '/upload/video-files',
  maxFilesize: 5, // megabytes
  chunkSize: 1000000 // bytes
}
);
thumbnaildropper.on('sending', function (file, xhr, formData) {
  formData.append('ospfilename', videofilename + '.png');
});
thumbnaildropper.on("uploadprogress", function (file, progress, bytesSent) {
  progress = Math.floor(bytesSent / file.size * 100);
  $('#thumbnailuploadprogress').width(progress + "%");
  document.getElementById('thumbnailuploadprogress').innerHTML = document.getElementById('thumbnailuploadprogress').innerHTML = '<b>' + progress + '%</b>';
});
thumbnaildropper.on("addedfile", function (file) {
  document.getElementById('thumbnailFilename').value = videofilename + '.png';
  document.getElementById('thumbnailFilenameDisplay').value = file.name;
  videouploadsocket();

});
thumbnaildropper.on("success", function (file) {
  document.getElementById('thumbnailuploadstatus').innerHTML = document.getElementById('thumbnailuploadstatus').innerHTML = ' <i class="fas fa-check">';
  document.getElementById('thumbnailuploadprogress').innerHTML = document.getElementById('thumbnailuploadprogress').innerHTML = 'Upload complete';

});
thumbnaildropper.on('error', function (file, response) {
  document.getElementById('thumbnailuploadstatus').innerHTML = document.getElementById('thumbnailuploadstatus').innerHTML = ' <i class="fas fa-exclamation-triangle"></i>';
  document.getElementById('thumbnailFilenameDisplay').value = 'Error: ' + response;
});

// Video Uploads
var videodropper = new Dropzone(
  '#videodropper', {
  acceptedFiles: 'video/mp4',
  createImageThumbnails: false,
  previewTemplate: '<div></div>',
  clickable: '#videouploadbutton',
  addRemoveLinks: true,
  paramName: 'file',
  chunking: true,
  forceChunking: true,
  url: '/upload/video-files',
  maxFilesize: 4096, // megabytes
  chunkSize: 1000000 // bytes
}
);

videodropper.on('sending', function (file, xhr, formData) {
  formData.append('ospfilename', videofilename + '.mp4');
});
videodropper.on("uploadprogress", function (file, progress, bytesSent) {
  progress = Math.floor(bytesSent / file.size * 100);
  $('#videouploadprogress').width(progress + "%");
  document.getElementById('videouploadprogress').innerHTML = document.getElementById('videouploadprogress').innerHTML = '<b>' + progress + '%</b>';
});
videodropper.on("addedfile", function (file) {
  document.getElementById('videoFilename').value = videofilename + '.mp4';
  document.getElementById('videoFilenameDisplay').value = file.name;
  videouploadsocket();

});
videodropper.on("success", function (file) {
  $('#uploadbutton').removeAttr('disabled');
  document.getElementById('videouploadstatus').innerHTML = document.getElementById('videouploadstatus').innerHTML = '<i class="fas fa-check">';
  document.getElementById('videouploadprogress').innerHTML = document.getElementById('videouploadprogress').innerHTML = 'Upload complete';
});
videodropper.on('error', function (file, response) {
  document.getElementById('videouploadstatus').innerHTML = document.getElementById('videouploadstatus').innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
  document.getElementById('videoFilenameDisplay').value = 'Error: ' + response;
});

$(document).ready(function () {
  $('.toast').toast('show');
  document.getElementById("uploadform").reset();

});

//Cancel Upload Cleanup
function canceluploads() {
  videodropper.removeAllFiles(true);
  thumbnaildropper.removeAllFiles(true);
  document.getElementById("uploadform").reset();
  document.getElementById('videouploadstatus').innerHTML = "";
  document.getElementById('videouploadprogress').innerHTML = document.getElementById('thumbnailuploadprogress').innerHTML = "";
  document.getElementById('thumbnailuploadstatus').innerHTML = "";
  document.getElementById('thumbnailuploadprogress').innerHTML = document.getElementById('thumbnailuploadprogress').innerHTML = "";
  $('#uploadbutton').attr('disabled');
  $('#thumbnailuploadprogress').width("0%");
  $('#videouploadprogress').width("0%");
}
