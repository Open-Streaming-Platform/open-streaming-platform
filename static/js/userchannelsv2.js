// User Channels Setup
var conn_options = {'sync disconnect on unload':true};
var socket = io();

Dropzone.autoDiscover = false;

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
  maxFilesize: 5, // megabytes
  chunkSize: 1000000 // bytes
}
);

// Event Listeners

window.addEventListener("beforeunload", function (e) {
  socket.emit('cancelUpload', { data: videofilename });
  return null;
});

$('#videoThumbnailUploadModal').on('hidden.bs.modal', function () {
    socket.emit('cancelUpload', { data: videofilename });
});

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

$(document).on("click", ".videoThumbnailUploadModalButton", function () {
    document.getElementById('videothumbnailuploadpreview').src = '/static/img/video-placeholder.jpg';
    var videoID = $(this).data('videoid');
    videofilename = s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();
    document.getElementById('videoThumbnailID').value = videoID;
    document.getElementById('videothumbnailFilenameDisplay').value = '';
    document.getElementById('videothumbnailFilename').value = '';
});

// Functions
function guid() {
      return s4() + s4() + '-' + s4() + '-' + s4() + '-' +
        s4() + '-' + s4() + s4() + s4();
    }

function s4() {
  return Math.floor((1 + Math.random()) * 0x10000)
    .toString(16)
    .substring(1);
}

function saveUploadedThumbnail() {
    var videoID = document.getElementById('videoThumbnailID').value;
    socket.emit('saveUploadedThumbnail', {videoID: videoID, thumbnailFilename: videofilename + '.png'} );
    var thumbnailDiv = document.getElementById('videoThumb-' + videoID);
    var thumbnailURL = thumbnailDiv.src;
    setTimeout(function() {
        thumbnailDiv.src = thumbnailURL + '?t=' + new Date().getTime();
    }, 4000);
    createNewBSAlert("Thumbnail Updated", "Success");
}