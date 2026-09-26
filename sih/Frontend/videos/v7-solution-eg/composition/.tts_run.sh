#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
while IFS=$'\t' read -r id text; do
  [ -z "$id" ] && continue
  npx --yes hyperframes@latest tts "$text" -v af_heart -s 0.94 -o "assets/voice/$id.wav" --json < /dev/null > ".tts_$id.json" 2>&1
  d=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "assets/voice/$id.wav" 2>/dev/null)
  echo "$id $d"
done < .tts_lines.tsv
echo DONE
