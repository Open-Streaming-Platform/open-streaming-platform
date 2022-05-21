This patch corrects an issue with nginx-rtmp HLS Keys being imported twice and causing failure when using the hls_key_path directive:
- Source: https://patch-diff.githubusercontent.com/raw/arut/nginx-rtmp-module/pull/1158.patch
- Original MR: https://github.com/arut/nginx-rtmp-module/pull/1158