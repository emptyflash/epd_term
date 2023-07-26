import time
import struct
import signal
import sys
import fcntl
import termios
from waveshare_epd import epd2in13_V3
from PIL import Image, ImageDraw, ImageChops, ImageFont

epd = epd2in13_V3.EPD()
epd.init()
epd.Clear(0xFF)

# we use the epd width and height flipped for landscape
font = ImageFont.load_default()
image = Image.new('1', (epd.height, epd.width), 255)  # 255: clear the frame
draw = ImageDraw.Draw(image)
_, _, font_width, font_height = draw.textbbox((0, 0), "M", font=font)

tty_width = epd.height // font_width
# Hacky, but subtract 3 for some reason
tty_height = epd.width // font_height - 3
with open("/dev/tty1", 'w') as tty:
    size = struct.pack("HHHH", int(tty_height), int(tty_width), 0, 0)
    fcntl.ioctl(tty.fileno(), termios.TIOCSWINSZ, size)

def split(s, n):
    """Split a sequence into parts of size n"""
    return [s[begin:begin + n] for begin in range(0, len(s), n)]

def band(bb):
    """Stretch a bounding box's X coordinates to be divisible by 8,
       otherwise weird artifacts occur as some bits are skipped."""
    return (int(bb[0] / 8) * 8, bb[1], int((bb[2] + 7) / 8) * 8, bb[3]) if bb else None

def sigint_handler(sig, frame):
    epd.init()
    epd.Clear(0xFF)
    epd.sleep()
    sys.exit(0)

def sigusr1_handler(sig, frame):
    epd.init()
    epd.displayPartBaseImage(epd.getbuffer(image))

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)
signal.signal(signal.SIGUSR1, sigusr1_handler)

old_buff = None
old_image = image
while True:
    image = Image.new('1', (epd.height, epd.width), 255)  # 255: clear the frame
    draw = ImageDraw.Draw(image)
    with open("/dev/vcsa1", 'rb') as f:
        attributes = f.read(4)
    with open("/dev/vcs1", "rb") as vcsu:
        buff = vcsu.read()
    rows, cols, cur_x, cur_y = list(map(ord, struct.unpack('cccc', attributes)))
    character_width = 1
    buff = split(buff, cols * character_width)[-tty_height:]
    buff = ''.join([r.decode('latin_1', 'replace') + '\n' for r in buff])

    draw.rectangle((0, 0, epd.height, epd.width), fill=255)
    draw.text((0,0), buff, font=font, fill=0)

    # TODO generalize this to different sizes and cursors
    adj_font_height = font_height + 4
    upper_left = (cur_x * font_width - 1, cur_y * adj_font_height - 2)
    lower_right = ((cur_x + 1) * font_width - 1, (cur_y + 1) * adj_font_height - 2)
    mask = Image.new('1', (image.width, image.height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle([upper_left, lower_right], fill=255)
    image = ImageChops.logical_xor(image, mask)

    image = image.transpose(Image.FLIP_TOP_BOTTOM)
    image = image.transpose(Image.FLIP_LEFT_RIGHT)
    if old_buff is None:
        epd.displayPartBaseImage(epd.getbuffer(image))
    elif ImageChops.difference(image, old_image).getbbox():
        epd.displayPartial(epd.getbuffer(image))
    else:
        time.sleep(0.1)
    old_buff = buff
    old_image = image
