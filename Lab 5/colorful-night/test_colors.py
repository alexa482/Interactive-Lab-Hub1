"""Hardware-independent tests: python -m unittest -v test_colors.py"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import cv2
import colorful_night as app
from colors import color_counts


class ColorTests(unittest.TestCase):
    def test_each_pixel_in_exactly_one_expected_bin(self):
        hsv = np.array([[[0,0,0],[0,0,100],[0,0,255],
            [0,255,255],[15,255,255],[28,255,255],[60,255,255],
            [90,255,255],[115,255,255],[140,255,255],[160,255,255]]],dtype=np.uint8)
        self.assertEqual(color_counts(cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)),[1]*11)

    def test_histogram_excludes_black_gray_keeps_white(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            app.save_report(root,[900,900,1,3,0,0,0,0,0,0,0],2,0,'Complete',app.Screen(False))
            report=json.loads((root/'summary.json').read_text())
            self.assertNotIn('black',report['percentages'])
            self.assertNotIn('gray',report['percentages'])
            self.assertEqual(report['percentages']['white'],25)
            self.assertEqual(report['percentages']['red'],75)
            with app.Image.open(root/'histogram.png') as image:
                self.assertEqual(image.size,(240,135))

    def test_no_retained_pixels(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            app.save_report(root,[50,50]+[0]*9,1,0,'Complete',app.Screen(False))
            self.assertEqual(sum(json.loads((root/'summary.json').read_text())['percentages'].values()),0)

    def test_scheduler_and_camera_failure(self):
        clock=[0.0]
        def sleep(seconds): clock[0]+=seconds
        values=[[0,0,0,100,0,0,0,0,0,0,0],RuntimeError('camera unavailable'),
                [0,0,0,0,0,0,100,0,0,0,0]]
        with tempfile.TemporaryDirectory() as d, patch('sys.argv',
            ['colorful_night.py','--start-now','--no-display','--hours',str(90/3600),
             '--interval','30','--output',d]), patch.object(app.time,'monotonic',side_effect=lambda:clock[0]), \
             patch.object(app.time,'sleep',side_effect=sleep), patch.object(app,'sample',side_effect=values):
            app.main()
            folder=next(Path(d).iterdir())
            report=json.loads((folder/'summary.json').read_text())
            self.assertEqual(report['samples'],2)
            self.assertEqual(report['failures'],1)
            self.assertEqual(report['status'],'With gaps')
            self.assertEqual(report['percentages']['red'],50)
            self.assertEqual(report['percentages']['green'],50)
            self.assertEqual(clock[0],93) # includes 3-second acknowledgement
            rows=[json.loads(v) for v in (folder/'night_log.jsonl').read_text().splitlines()]
            self.assertEqual([r['elapsed_s'] for r in rows],[0,30,60])


if __name__=='__main__':
    unittest.main()
