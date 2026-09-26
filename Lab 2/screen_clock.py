import time
import subprocess
from pathlib import Path
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789

# Configuration for CS and DC pins (these are FeatherWing defaults on M0/M4):
cs_pin = digitalio.DigitalInOut(board.D5) 
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None

# Config for display baudrate (default max is 24mhz):
BAUDRATE = 64000000

# Setup SPI bus using hardware SPI:
spi = board.SPI()

# Create the ST7789 display:
disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

# Create blank image for drawing.
# Make sure to create image with mode 'RGB' for full color.
height = disp.width  # we swap height/width to rotate it to landscape!
width = disp.height
image = Image.new("RGB", (width, height))
rotation = 90

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))
disp.image(image, rotation)
# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Alternatively load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)

# Turn on the backlight
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

button = digitalio.DigitalInOut(board.D23)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP


def animation(filename, number_of_frames, time_between_frames):
    for frame_number in range(1, number_of_frames + 1):
        frame_path = Path(__file__).parent / "animation" / f"{filename}{frame_number}.png"
        with Image.open(frame_path) as source:
            frame = source.convert("RGB").resize((width, height))
        disp.image(frame, rotation)
        time.sleep(time_between_frames)



current_hour = int(time.strftime("%H"))

if 6 <= current_hour < 12:
    current_period = 0    
elif 12 <= current_hour < 17:
    current_period = 1     
elif 17 <= current_hour < 21:
    current_period = 2      
else:
    current_period = 3      

previous_button = True
while True:
    current_button = button.value
    if previous_button and not current_button:
        current_period = (current_period + 1) % 4
        time.sleep(0.2) 
    previous_button = current_button
    if current_period == 0:
        shiba_image = "shibamorning.png"
    elif current_period == 1:
        shiba_image = "shibaafternoon.png"
    elif current_period == 2:
        shiba_image = "shibaevening.png"
    else:
        shiba_image = "shibanight.png"
    shiba = Image.open(shiba_image)
    shiba = shiba.resize((width, height))
    shiba = shiba.convert("RGB")
    disp.image(shiba, rotation)

    time.sleep(0.01)
   


        

