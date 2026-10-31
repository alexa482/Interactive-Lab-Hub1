"""Color classification adapted from Lab 5/coyote_colors.py."""
COLORS = [('black', '#171923'), ('gray', '#91969e'), ('white', '#f1f3f5'),
          ('red', '#e44747'), ('orange', '#ed943e'), ('yellow', '#e6cf48'),
          ('green', '#53a65d'), ('cyan', '#4fbfc6'), ('blue', '#4876ce'),
          ('purple', '#9860c4'), ('pink', '#d85b9c')]


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

