#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-18 Richard Hull and contributors
# See LICENSE.rst for details.

import re
import time
import argparse
import RPi.GPIO as GPIO

import logging
import os
import subprocess
import sys

import gphoto2 as gp

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT, LCD_FONT

from wand.image import Image

def demo(photo_count, countdown_from):

    # create matrix device
    serial = spi(port=0, device=0, gpio=noop())
    device = max7219(serial, cascaded=4, block_orientation=-90, rotate=0)
    print("Created device")

    # setup button on Raspberry Pi Pin 18

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    while True:
        print("PUSH THE BUTTON!")
	with canvas(device) as draw:
		text(draw, (1, 0), "Ready", fill="white", font=proportional(LCD_FONT))

        GPIO.wait_for_edge(18, GPIO.FALLING)

        print('Button Pressed')

        # Start by creating a folder for all the photos, with a folder inside called minis for gif-based

        time_now = time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())
        pi_folder = os.path.join('/home/pi/wedding_photos/', time_now)
        minis_folder = os.path.join(pi_folder, 'minis')
        os.makedirs(minis_folder)

        gif_folder = os.path.join('/home/pi/wedding_photos/gifs/')
        # os.makedirs(gif_folder)


        # Start looping and taking photos!

        for index in range(photo_count):
	  msg = ""
          for i in range(countdown_from):

	    msg += "%s... " %(countdown_from - i)

	  show_message(device, msg, fill="white", font=proportional(LCD_FONT), scroll_delay=0.05)

	  with canvas(device) as draw:
            text(draw, (2, 0), "Smile!", fill="white", font=proportional(LCD_FONT))

          # GPHOTO

          logging.basicConfig(
            format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
          gp.check_result(gp.use_python_logging())
          camera = gp.check_result(gp.gp_camera_new())
          gp.check_result(gp.gp_camera_init(camera))
          print('Capturing image')
          file_path = gp.check_result(gp.gp_camera_capture(
            camera, gp.GP_CAPTURE_IMAGE))
          print('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))

          # save image to pi
          target = os.path.join(pi_folder, time.strftime("%Y%m%d%H%M%S", time.gmtime()) + file_path.name)

          print('Copying image to', target)
          camera_file = gp.check_result(gp.gp_camera_file_get(
            camera, file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL))
          gp.check_result(gp.gp_file_save(camera_file, target))

          # subprocess.call(['xdg-open', target]) # Commented out as no need to open

          gp.check_result(gp.gp_camera_exit(camera))

          ## GPHOTO END

          device.clear()

        # OK, let's create a gif! First, let's create some smaller images

        for filename in os.listdir(pi_folder):
            if filename.endswith(".jpg"):
                img = Image(filename=os.path.join(pi_folder, filename))
                img.sample(780, 540)
                img.save(filename=os.path.join(minis_folder, filename))
            else:
                continue

        # Create a gif from them smaller images

        with Image() as wand:
            for filename in os.listdir(minis_folder):
                if filename.endswith(".jpg"):
                    with Image(filename=os.path.join(minis_folder, filename)) as photo:
                        wand.sequence.append(photo)
                else:
                    continue
            for cursor in range(len(wand.sequence)):
                with wand.sequence[cursor] as frame:
                    frame.delay = 50
            wand.type = 'optimize'
            wand.save(filename=os.path.join(gif_folder, "{0}.gif".format(time_now)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='gphoto arguments',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # parser.add_argument('--cascaded', '-n', type=int, default=1, help='Number of cascaded MAX7219 LED matrices')
    # parser.add_argument('--block-orientation', type=int, default=0, choices=[0, 90, -90], help='Corrects block orientation when wired vertically')
    # parser.add_argument('--rotate', type=int, default=2, choices=[0, 1, 2, 3], help='Rotate display 0=0°, 1=90°, 2=180°, 3=270°')
    parser.add_argument('--photo-count', type=int, default=3, help='How many photos to take')

    parser.add_argument('--countdown-from', type=int, default=5, help='What number to countdown from')

    args = parser.parse_args()

    try:
        demo(args.photo_count, args.countdown_from)
    except KeyboardInterrupt:
        GPIO.cleanup()       # clean up GPIO on CTRL+C exit
        pass
    GPIO.cleanup()           # clean up GPIO on normal exit
