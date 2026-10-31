#!/usr/bin/env python3
"""Voice-triggered overnight window colors for a USB webcam and 1.14-inch Mini PiTFT."""
import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont
from colors import COLORS, color_counts

ROOT = Path(__file__).resolve().parent


def stamp():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def font(size=12):
    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default()


def message(*lines):
    image = Image.new('RGB', (240, 135), '#10151e')
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(lines):
        draw.text((8, 10+i*23), line, font=font(13), fill='white')
    return image


def histogram(totals, samples, failures, status):
    image = Image.new('RGB', (240, 135), '#10151e')
    d = ImageDraw.Draw(image)
    kept = sum(totals[2:])  # never plot black or gray; white is retained
    d.text((5, 2), 'Your night in color', font=font(13), fill='white')
    if not samples or not kept:
        d.text((8, 48), 'No colors detected' if samples else 'No valid camera samples',
               font=font(13), fill='white')
    else:
        # Fixed 0–100% scale. Each letter sits beneath its matching color bar.
        d.text((2, 24), '100%', font=font(9), fill='white')
        d.text((12, 87), '0', font=font(9), fill='white')
        d.line((30, 28, 30, 99), fill='#8694a8')
        d.line((30, 99, 235, 99), fill='#8694a8')
        for i, (name, color) in enumerate(COLORS[2:]):
            pct = 100 * totals[i+2] / kept
            x = 34 + i*22
            height = round(pct*.70)
            if height:
                d.rectangle((x, 99-height, x+16, 98), fill=color)
            d.text((x, 100), name[:1].upper(), font=font(10), fill=color)
    d.text((4, 117), f'{status} | {samples} frames | {failures} missed',
           font=font(10), fill='white')
    return image


class Screen:
    def __init__(self, enabled):
        self.device = None
        if enabled:
            import board
            import digitalio
            from adafruit_rgb_display import st7789
            self.cs = digitalio.DigitalInOut(board.CE0)
            self.dc = digitalio.DigitalInOut(board.D25)
            self.device = st7789.ST7789(board.SPI(), cs=self.cs, dc=self.dc,
                rst=None, baudrate=24000000, width=135, height=240,
                x_offset=53, y_offset=40, rotation=90)
            self.light = digitalio.DigitalInOut(board.D22)
            self.light.switch_to_output(value=True)

    def show(self, image):
        if self.device:
            self.light.value = True
            self.device.image(image)

    def dark(self):
        if self.device:
            self.light.value = False


def capture(camera, roi):
    """Runs in a bounded subprocess; reopen so queued overnight frames cannot accumulate."""
    import cv2
    cap = cv2.VideoCapture(camera, cv2.CAP_V4L2)
    try:
        if not cap.isOpened():
            raise RuntimeError('Cannot open USB webcam')
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        until = time.monotonic()+1.5  # allow auto exposure to settle
        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError('Webcam returned no frame')
            if time.monotonic() >= until:
                break
        x, y, w, h = roi
        fh, fw = frame.shape[:2]
        crop = frame[int(y*fh):int((y+h)*fh), int(x*fw):int((x+w)*fw)]
        if not crop.size:
            raise RuntimeError('Window crop is empty')
        print(json.dumps(color_counts(crop)), flush=True)
    finally:
        cap.release()


def sample(args, timeout):
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
        '--capture', '--camera', str(args.camera), '--roi', *map(str,args.roi)],
        capture_output=True, text=True, timeout=timeout, check=True)
    counts = json.loads(result.stdout)
    if len(counts) != len(COLORS) or any(type(n) is not int or n < 0 for n in counts) or not sum(counts):
        raise RuntimeError('Invalid color counts')
    return counts


def save_report(folder, totals, samples, failures, status, screen):
    image = histogram(totals, samples, failures, status)
    image.save(folder/'histogram.png')
    kept = sum(totals[2:])
    summary = dict(status=status, samples=samples, failures=failures,
        retained_percent=100*kept/sum(totals) if sum(totals) else 0,
        percentages={name:100*n/kept if kept else 0
                     for (name,_),n in zip(COLORS[2:],totals[2:])})
    (folder/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    screen.show(image)
    print(f'Result saved in {folder}', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hours', type=float, default=8)
    p.add_argument('--interval', type=float, default=30)
    p.add_argument('--camera', type=int, default=0)
    p.add_argument('--mic', type=int, help='sounddevice input index')
    p.add_argument('--vad-model', type=Path, default=ROOT/'models/silero_vad.onnx')
    p.add_argument('--roi', type=float, nargs=4, default=[0,0,1,1], metavar=('X','Y','W','H'))
    p.add_argument('--output', type=Path, default=ROOT/'color_runs')
    p.add_argument('--start-now', action='store_true', help='skip spoken trigger')
    p.add_argument('--no-display', action='store_true', help='save chart without GPIO hardware')
    p.add_argument('--test', action='store_true', help='60 seconds, a sample every 5 seconds')
    p.add_argument('--capture', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--report', type=Path, help='redisplay an existing run, without voice/camera')
    args = p.parse_args()
    if not all(math.isfinite(v) for v in [args.hours,args.interval,*args.roi]) or args.hours <= 0 or args.interval <= 0:
        p.error('hours and interval must be finite and positive')
    x,y,w,h = args.roi
    if min(x,y)<0 or min(w,h)<=0 or x+w>1 or y+h>1:
        p.error('ROI must fit inside normalized coordinates 0..1')
    if args.capture:
        capture(args.camera,args.roi)
        return
    # Prevent two instances from competing for the microphone, webcam, or screen.
    import fcntl
    lock = (ROOT/'.running.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        p.error('Another colorful-night instance is already running')
    screen = Screen(not args.no_display)
    folder = None
    totals, samples, failures = [0]*len(COLORS), 0, 0
    status = 'Complete'
    try:
        if args.report:
            screen.show(Image.open(args.report/'histogram.png').convert('RGB'))
        else:
            if not args.start_now:
                screen.show(message('Say:', 'Have a colorful night', 'Loading listener...'))
                from voice import wait_for_phrase
                screen.show(message('Say:', 'Have a colorful night', 'Wait for acknowledgement'))
                wait_for_phrase(args.vad_model,args.mic)
            duration = 60 if args.test else args.hours*3600
            interval = 5 if args.test else args.interval
            folder = args.output / dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            folder.mkdir(parents=True)
            (folder/'settings.json').write_text(json.dumps(dict(started=stamp(),
                duration_seconds=duration, interval_seconds=interval,
                camera=args.camera, roi=args.roi),indent=2))
            screen.show(message('Goodnight!', f'Watching for {duration/3600:g} hours',
                                'Your colors await at dawn.'))
            time.sleep(3)
            screen.dark()
            start = time.monotonic()
            end = start+duration
            due = start
            with (folder/'night_log.jsonl').open('a') as log:
                while due < end:
                    time.sleep(max(0,min(due,end)-time.monotonic()))
                    remaining = end-time.monotonic()
                    if remaining <= 0:
                        break
                    row = dict(t=stamp(),elapsed_s=round(time.monotonic()-start,2))
                    try:
                        counts = sample(args, min(12,remaining))
                        # Per-frame fractions give every valid sample equal weight.
                        totals = [a+b/sum(counts) for a,b in zip(totals,counts)]
                        samples += 1
                        row['counts'] = counts
                    except (subprocess.SubprocessError,ValueError,RuntimeError) as exc:
                        failures += 1
                        row['error'] = str(exc)
                        print(f'Camera sample missed: {exc}',flush=True)
                    log.write(json.dumps(row)+'\n')
                    log.flush()
                    os.fsync(log.fileno())
                    due += interval
                    # Skip missed slots instead of burst-capturing old deadlines.
                    while due < time.monotonic() and due < end:
                        failures += 1
                        log.write(json.dumps(dict(t=stamp(),error='Missed scheduled slot',
                                                  elapsed_s=round(due-start,2)))+'\n')
                        log.flush()
                        due += interval
                time.sleep(max(0,end-time.monotonic()))
            if failures:
                status = 'With gaps'
            save_report(folder,totals,samples,failures,status,screen)
        print('Histogram stays visible. Ctrl-C exits; rerun for the next night.',flush=True)
        if not args.no_display:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        if folder and not (folder/'summary.json').exists():
            save_report(folder,totals,samples,failures,'Stopped early',screen)
    except Exception:
        screen.show(message('Something went wrong', 'See terminal for details'))
        raise


if __name__ == '__main__':
    main()
