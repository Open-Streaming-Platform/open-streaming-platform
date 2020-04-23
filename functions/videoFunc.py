import subprocess

# Checks Length of a Video at path and returns the length
def getVidLength(input_video):
    result = subprocess.check_output(['ffprobe', '-i', input_video, '-show_entries', 'format=duration', '-loglevel', '8', '-of', 'csv=%s' % ("p=0")])
    return float(result)