# Have a colorful night

For a Raspberry Pi running 64-bit Raspberry Pi OS, USB webcam and microphone, and Adafruit 1.14-inch Mini PiTFT (240 × 135). Prepared for Alexa's Lab 5; hardware testing is still required.

Say **“Have a colorful night”** and wait for “Goodnight!” on the screen. After a three-second acknowledgement, the backlight turns off. The Pi samples the webcam every 30 seconds for eight hours, then turns on the screen with a histogram. The microphone closes after the trigger. Each new night requires rerunning the command. No images or audio are saved; timestamped color counts stay on the Pi.

## Install on the Pi

Copy this whole folder into your repository's `Lab 5` directory. Open a terminal **on the Pi**, change into this folder, and run:

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev libportaudio2 portaudio19-dev fonts-dejavu-core tmux
sudo raspi-config
```

In raspi-config, enable **Interface Options → SPI**, then reboot if requested. This uses direct SPI access through Adafruit Blinka. If the Mini PiTFT currently mirrors a Linux console/desktop using a kernel framebuffer driver, follow Adafruit's guide to disable that competing driver before using this program. Close other programs using the display or webcam.

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p models
curl -fL https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx -o models/silero_vad.onnx
python -c 'from faster_whisper import WhisperModel; WhisperModel("tiny.en", device="cpu", compute_type="int8")'
```

Internet is required for setup and model downloads. Speech recognition is offline during use. This uses the same VAD/Whisper approach as Lab 3. If Lab 3 is already set up, you may reuse its working environment and pass `--vad-model /path/to/silero_vad.onnx`. Platform-dependent dependencies may need the lab's existing setup, especially on older or 32-bit operating systems.

## Try a one-minute night first

```bash
source .venv/bin/activate
python colorful_night.py --test --start-now
```

The test collects samples every five seconds for one minute. Point the webcam at colorful objects. The screen should acknowledge, go dark, and show a chart after a minute. Then test the voice trigger:

```bash
python colorful_night.py --test
```

Speak the phrase exactly and wait for the acknowledgement before walking away. This is speech transcription with exact normalized phrase matching, not a trained wake-word model; background speech, accents and recognition errors can affect triggering. Audio from a TV saying the phrase can trigger it too. Model loading may take a little time.

## Run overnight

```bash
tmux new -s colors
source .venv/bin/activate
python colorful_night.py
```

Say “Have a colorful night.” Once acknowledged, detach from tmux with **Ctrl-B, then D**. You can disconnect your laptop; keep the Pi powered. Return with `tmux attach -t colors`. The program remains running with the morning chart visible. Ctrl-C exits; rerun for another night.

## Results and controls

Each run creates its own folder in `color_runs/`:

- `night_log.jsonl`: timestamped counts for successful frames and explicit errors/missed slots.
- `settings.json`: duration, interval, camera index and window crop.
- `summary.json`: overall percentages, number of samples, gaps and retained-pixel percentage.
- `histogram.png`: the exact 240 × 135 image sent to the display.

The histogram always excludes **black and gray**. Remaining categories, in display order, are **White, Red, Orange, Yellow, Green, Cyan, Blue, Purple, Pink**. Letters under the bars correspond to that order; the bars themselves identify their colors. The vertical scale is fixed at 0–100%. Exact percentages are in `summary.json`.

Every valid frame has equal weight. We average category proportions over valid frames, then exclude black and gray and renormalize the remainder to 100%. A nearly dark night can consequently show a large percentage for a small colored light; `retained_percent` reports how much of the original scene remains. If no retained pixels exist, the display says “No colors detected.” If the camera never succeeds, it says “No valid camera samples.”

Useful options:

```bash
python -m sounddevice                         # list microphone indices
python colorful_night.py --mic 2 --camera 0   # select input devices
python colorful_night.py --roi .1 .1 .8 .8    # crop to central window area
python colorful_night.py --hours 8 --interval 30
python colorful_night.py --test --start-now --no-display
python colorful_night.py --report color_runs/YOUR_RUN_FOLDER
```

ROI numbers are normalized x, y, width, height, each in 0–1. Keep the camera fixed, avoid indoor reflections, and adjust framing during the test. These are camera-observed colors, affected by exposure, white balance and low-light noise. Black means HSV value below 45/255; gray uses saturation below 45/255 and value below 200/255. Those are inherited from the existing lab prototype and may need tuning after a real night.

Capture reopens the webcam for each sample, allows 1.5 seconds of exposure settling, then closes it. A subprocess timeout prevents a hung camera read from blocking the whole night. Default captures are scheduled 30 seconds apart; a failed/slow capture can reduce the expected 960 samples. Test low-light exposure on your particular webcam. Logs flush to disk after each capture; interrupted runs are not automatically resumed after power loss. Ctrl-C during recording produces a partial report. A second instance is blocked to prevent device conflicts.

## Lab documentation / acknowledgements

Before bed: the spoken phrase hands the night over; the display acknowledges and darkens. Asleep: camera samples become local timestamped color measurements. Awake: the histogram reveals the window's overnight palette.

Adapted from [Lab 5/coyote_colors.py](https://github.com/alexa482/Interactive-Lab-Hub1/blob/Fall2026/Lab%205/coyote_colors.py) and [Lab 3/listen.py](https://github.com/alexa482/Interactive-Lab-Hub1/blob/Fall2026/Lab%203/speech-scripts/listen.py). Mini PiTFT configuration follows [Adafruit's example](https://github.com/adafruit/Adafruit_CircuitPython_RGB_Display/blob/main/examples/rgb_display_minipitfttest.py) and [Python guide](https://learn.adafruit.com/adafruit-mini-pitft-135x240-color-tft-add-on-for-raspberry-pi/python-usage). Prepared with assistance from OpenAI Codex. Add your own test results, photos, storyboard and real overnight data to the lab submission; this package does not claim those tests have happened.
