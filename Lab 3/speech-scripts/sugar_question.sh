#!/usr/bin/env bash

set -euo pipefail
echo "Asking question..."
python3 -m piper \
  --model en_US-lessac-medium \
  --data-dir ../voices \
  --output-raw \
  -- "How many sugars would you like in your tea? How many pats of butter would you like on your scone? And how many strawberries would you like on your cake?" \
  | aplay -r 22050 -f S16_LE -t raw -
echo
echo "Recording your answer for 5 seconds..."
arecord \
  -d 5 \
  -f S16_LE \
  -c 1 \
  -r 16000 \
  sugar_answer.wav
echo
echo "Transcribing..."
python3 transcribe.py sugar_answer.wav --model tiny.en