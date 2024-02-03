
function s4() {
  return Math.floor((1 + Math.random()) * 0x10000)
    .toString(16)
    .substring(1);
}

const bytesInOneMebibyte = 1048576;
videofilename = s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();

// Used for Video Upload Cancel Cleanup
function videouploadsocket() {

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
  maxFilesize: maxThumbnailUploadFileSize, // mebibytes
  chunkSize: bytesInOneMebibyte
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
  maxFilesize: maxVideoUploadFileSize, // mebibytes
  chunkSize: bytesInOneMebibyte
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

// Thumbnail Only Uploader

// Dropper Configuration
var uploadthumbnaildropper = new Dropzone(
  '#videothumbnaildropper', {
  acceptedFiles: 'image/png',
  previewTemplate: '<div></div>',
  clickable: '#videothumbnailuploadbutton',
  addRemoveLinks: true,
  paramName: 'file',
  chunking: true,
  forceChunking: true,
  url: '/upload/video-files',
  maxFilesize: maxThumbnailUploadFileSize, // mebibytes
  chunkSize: bytesInOneMebibyte
}
);

uploadthumbnaildropper.on('sending', function (file, xhr, formData) {
  formData.append('ospfilename', videofilename + '.png');
});

uploadthumbnaildropper.on("uploadprogress", function (file, progress, bytesSent) {
  progress = Math.floor(bytesSent / file.size * 100);
  $('#videothumbnailuploadprogress').width(progress + "%");
  document.getElementById('videothumbnailuploadprogress').innerHTML = document.getElementById('videothumbnailuploadprogress').innerHTML = '<b>' + progress + '%</b>';
});

uploadthumbnaildropper.on("addedfile", function (file) {
  document.getElementById('videothumbnailFilename').value = videofilename + '.png';
  document.getElementById('videothumbnailFilenameDisplay').value = file.name;
  videouploadsocket();
});

uploadthumbnaildropper.on("success", function (file) {
  document.getElementById('videothumbnailuploadstatus').innerHTML = document.getElementById('videothumbnailuploadstatus').innerHTML = ' <i class="fas fa-check">';
  document.getElementById('videothumbnailuploadprogress').innerHTML = document.getElementById('videothumbnailuploadprogress').innerHTML = 'Upload complete';
  document.getElementById('videothumbnailuploadpreview').src = '/videos/temp/' + videofilename + '.png';
});

uploadthumbnaildropper.on('error', function (file, response) {
  document.getElementById('videothumbnailuploadstatus').innerHTML = document.getElementById('videothumbnailuploadstatus').innerHTML = ' <i class="fas fa-exclamation-triangle"></i>';
  document.getElementById('videothumbnailFilenameDisplay').value = 'Error: ' + response;
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
