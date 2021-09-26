// Admin Page Viewer Chart
var ctx = document.getElementById('viewershipChart').getContext('2d');
ctx.canvas.width = viewerChartWidth;
ctx.canvas.height = viewerChartHeight;
var chart = new Chart(ctx, {
    responsive:false,
    maintainAspectRatio: false,
    // The type of chart we want to create
    type: 'bar',

    // The data for our dataset
    data: {
        datasets: [
            {
            label: "Live Viewers",
            fill: true,
            borderColor: 'rgb(40, 90, 150)',
            backgroundColor: 'rgb(40, 90, 150)',
            spanGaps: true,
            lineTension: 0,
            data: viewerChartDataLive
            },
            {
            label: "Video Viewers",
            fill: true,
            borderColor: 'rgb(90, 150, 40)',
            backgroundColor: 'rgb(90, 150, 40)',
            spanGaps: true,
            lineTension: 0,
            data:viewerChartDataVideo
        }]
    },

    // Configuration options go here
    options: {
        scales: {
            xAxes: [{
                type: 'time',
                time: {
                    parser: 'YYYY-MM-DD',
                    unit: 'day'
                }
            }],
        }
    }
});