"""Quiet-coyote-triggered window color recorder for Lab 5's USB webcam."""
import argparse
import datetime as dt
import html
import json
import math
from pathlib import Path
import time

COLORS = [('black', '#171923'), ('gray', '#91969e'), ('white', '#f1f3f5'),
          ('red', '#e44747'), ('orange', '#ed943e'), ('yellow', '#e6cf48'),
          ('green', '#53a65d'), ('cyan', '#4fbfc6'), ('blue', '#4876ce'),
          ('purple', '#9860c4'), ('pink', '#d85b9c')]


def quiet_coyote(points):
    """Index/pinky extended; thumb touches curled middle/ring. Pixel coordinates."""
    def distance(a, b):
        return math.dist(points[a], points[b])
    palm = distance(0, 9)
    if palm < 10:
        return False
    extended = all(distance(tip, 0) > distance(pip, 0) * 1.2
                   for tip, pip in [(8, 6), (20, 18)])
    return (extended and distance(4, 12) < palm * .65
            and distance(4, 16) < palm * .65
            and distance(8, 4) > palm * .7
            and distance(20, 16) > palm * .6)


def color_counts(frame):
    import cv2
    import numpy as np
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    # OpenCV hue is 0..179. Every pixel belongs to exactly one bin.
    labels = np.zeros(h.shape, dtype=np.uint8)
    visible = v >= 45
    neutral = visible & (s < 45)
    labels[neutral & (v < 200)] = 1
    labels[neutral & (v >= 200)] = 2
    chromatic = visible & ~neutral
    hue_bins = [(3, 0, 10), (4, 10, 23), (5, 23, 35), (6, 35, 85),
                (7, 85, 100), (8, 100, 130), (9, 130, 150), (10, 150, 170),
                (3, 170, 180)]
    for label, lo, hi in hue_bins:
        labels[chromatic & (h >= lo) & (h < hi)] = label
    return np.bincount(labels.ravel(), minlength=len(COLORS)).tolist()


def report(folder, status):
    rows = [json.loads(line) for line in (folder / 'night_log.jsonl').read_text(encoding='utf-8').splitlines()]
    if not rows:
        print('No color samples collected; no histogram generated.', flush=True)
        return
    # At most 120 time bins, so overnight charts stay legible.
    chunk = max(1, math.ceil(len(rows) / 120))
    groups = [rows[i:i + chunk] for i in range(0, len(rows), chunk)]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 450">',
           '<rect width="1000" height="450" fill="white"/>',
           '<g font-family="sans-serif" font-size="14" fill="#222">',
           '<text x="65" y="24">Window colors — pixel share over time</text>']
    for pct in [0, 25, 50, 75, 100]:
        y = 350 - pct * 3
        svg.append(f'<text x="15" y="{y+5}">{pct}%</text>')
    for i, group in enumerate(groups):
        counts = [sum(row['counts'][j] for row in group) for j in range(len(COLORS))]
        total, bottom = sum(counts), 350.0
        width = 900 / len(groups)
        for (name, color), count in zip(COLORS, counts):
            height = 300 * count / total
            bottom -= height
            svg.append(f'<rect x="{65+i*width:.2f}" y="{bottom:.2f}" width="{width:.2f}" height="{height:.2f}" fill="{color}"><title>{name}: {100*count/total:.1f}% at {group[0]["elapsed_s"]:.1f}s</title></rect>')
    svg.extend([f'<text x="65" y="380">{rows[0]["elapsed_s"]:.1f}s</text>',
                f'<text x="900" y="380">{rows[-1]["elapsed_s"]:.1f}s</text>',
                '<text x="370" y="410">Seconds since sensing started</text></g></svg>'])
    chart = ''.join(svg)
    (folder / 'histogram.svg').write_text(chart, encoding='utf-8')
    totals = [sum(row['counts'][j] for row in rows) for j in range(len(COLORS))]
    total = sum(totals)
    legend = ''.join(f'<tr><td><span style="display:inline-block;width:20px;height:16px;background:{color}"></span> {name}</td><td>{100*n/total:.2f}%</td></tr>' for (name, color), n in zip(COLORS, totals))
    (folder / 'report.html').write_text(f'''<!doctype html><meta charset="utf-8"><title>Window color report</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;background:#fafafa}}td{{padding:5px 20px}}svg{{width:100%}}</style>
<h1>Window color report</h1><p>{len(rows)} samples · {html.escape(status)} · Started {html.escape(rows[0]['t'])}</p>
{chart}<h2>Overall color distribution</h2><table>{legend}</table>
<p>Each stacked bar represents the pixel distribution in a time bin. All pixels are included, grouped into 11 broad color categories. Dark pixels count as black; these are camera-observed colors, affected by lighting, reflections, exposure, and white balance.</p>''', encoding='utf-8')
    print(f'Report: {(folder / "report.html").resolve()}', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report-only', type=Path, metavar='RUN_FOLDER', help='rebuild report from an existing run; no camera needed')
    p.add_argument('--duration', type=float, default=60, help='sensing seconds, after gesture and settle delay')
    p.add_argument('--interval', type=float, default=2, help='seconds between samples')
    p.add_argument('--settle', type=float, default=5, help='seconds to remove hand / aim camera')
    p.add_argument('--hold', type=float, default=1, help='continuous gesture hold in seconds')
    p.add_argument('--camera', type=int, default=0)
    p.add_argument('--preview', action='store_true', help='show camera window; requires desktop/VNC')
    p.add_argument('--start-now', action='store_true', help='skip gesture for camera/color debugging')
    p.add_argument('--roi', type=float, nargs=4, metavar=('X', 'Y', 'W', 'H'), default=[0, 0, 1, 1], help='normalized window crop; gesture uses full frame')
    p.add_argument('--output', type=Path, default=Path('color_runs'))
    args = p.parse_args()
    if args.report_only is not None:
        report(args.report_only, 'Regenerated from saved readings')
        return
    if not all(math.isfinite(v) for v in [args.duration, args.interval, args.settle, args.hold, *args.roi]) or min(args.duration, args.interval, args.hold) <= 0 or args.settle < 0:
        p.error('duration, interval, hold must be positive; settle nonnegative; values finite')
    x, y, w, h = args.roi
    if min(x, y) < 0 or min(w, h) <= 0 or x+w > 1 or y+h > 1:
        p.error('ROI must fit inside normalized frame coordinates 0..1')
    import cv2
    cap = cv2.VideoCapture(args.camera)
    hands = None
    folder = None
    status = 'Completed'
    try:
        if not cap.isOpened():
            raise RuntimeError('Cannot open webcam. Check --camera and close other camera programs.')
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not args.start_now:
            import mediapipe as mp
            hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=.7, min_tracking_confidence=.6)
        print('Waiting: hold quiet coyote (index + pinky up, thumb touching middle + ring).', flush=True)
        held_since = None
        settle_until = time.monotonic() + args.settle if args.start_now else None
        start = None
        next_sample = 0
        failures = 0
        # Read continuously rather than letting stale frames collect between samples.
        while True:
            now = time.monotonic()
            if start is not None and now-start >= args.duration:
                break
            ok, frame = cap.read()
            if not ok:
                held_since = None
                failures += 1
                if failures >= 20:
                    raise RuntimeError('Camera stopped returning frames.')
                time.sleep(.05)
                continue
            failures = 0
            now = time.monotonic()
            if settle_until is None:
                result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                detected = False
                if result.multi_hand_landmarks:
                    pts = [(v.x*frame.shape[1], v.y*frame.shape[0]) for v in result.multi_hand_landmarks[0].landmark]
                    detected = quiet_coyote(pts)
                held_since = (held_since if held_since is not None else now) if detected else None
                if held_since is not None and now-held_since >= args.hold:
                    settle_until = now + args.settle
                    hands.close()
                    hands = None
                    print(f'Signal accepted! Aim at window; sensing starts in {args.settle:g}s.', flush=True)
            elif now >= settle_until:
                if start is None:
                    folder = args.output / dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                    folder.mkdir(parents=True, exist_ok=False)
                    (folder / 'settings.json').write_text(json.dumps(vars(args), default=str, indent=2), encoding='utf-8')
                    start = now
                    print(f'Sensing for {args.duration:g}s...', flush=True)
                if now-start >= args.duration:
                    break
                if now >= next_sample:
                    fh, fw = frame.shape[:2]
                    crop = frame[int(y*fh):int((y+h)*fh), int(x*fw):int((x+w)*fw)]
                    if crop.size == 0:
                        raise RuntimeError('ROI is smaller than one pixel.')
                    counts = color_counts(crop)
                    row = {'t': dt.datetime.now().astimezone().isoformat(), 'elapsed_s': round(now-start, 3), 'counts': counts, 'colors': [v[0] for v in COLORS]}
                    with (folder / 'night_log.jsonl').open('a', encoding='utf-8') as log:
                        log.write(json.dumps(row)+'\n')
                    next_sample = now + args.interval
            if args.preview:
                label = 'Hold quiet coyote' if settle_until is None else ('Aim at window' if start is None else f'Sensing {now-start:.0f}/{args.duration:g}s')
                cv2.putText(frame, label, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 0), 2)
                cv2.imshow('Window colors (q stops)', frame)
                if cv2.waitKey(1) & 255 == ord('q'):
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        status = 'Stopped early'
    except Exception as exc:
        status = f'Failed: {exc}'
        raise
    finally:
        cap.release()
        if hands is not None:
            hands.close()
        if args.preview:
            cv2.destroyAllWindows()
        if folder is not None and (folder / 'night_log.jsonl').exists():
            report(folder, status)


if __name__ == '__main__':
    main()
