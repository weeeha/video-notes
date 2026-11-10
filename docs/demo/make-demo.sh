#!/usr/bin/env bash
# Builds docs/demo/out/demo-feedback.mp4: three stills of app.html with a cursor ring, each with a spoken note (macOS `say`).
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p out
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
shot() { "$CHROME" --headless=new --hide-scrollbars --window-size=1600,900 --screenshot="out/$1.png" "file://$PWD/app.html?x=$2&y=$3" >/dev/null 2>&1; }
shot s1 120 623; shot s2 1537 192; shot s3 1200 360
say -o out/a1.aiff "The search field is buried at the bottom of the sidebar. Move it up into the header."
say -o out/a2.aiff "This export button is way too small, and the label is grey on grey. Make it bigger and darker."
say -o out/a3.aiff "These two date columns say the same thing. Drop one of them. Later we could add sorting, but not now."
parts=()
for i in 1 2 3; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 out/a$i.aiff)
  ffmpeg -v error -y -loop 1 -i out/s$i.png -i out/a$i.aiff -af apad=pad_dur=1.5 -t "$(echo "$d+1.5" | bc)" \
    -c:v libx264 -pix_fmt yuv420p -r 30 -c:a aac -ar 44100 out/p$i.mp4
  parts+=("file 'p$i.mp4'")
done
printf '%s\n' "${parts[@]}" > out/list.txt
ffmpeg -v error -y -f concat -safe 0 -i out/list.txt -c copy out/demo-feedback.mp4
echo "out/demo-feedback.mp4"
