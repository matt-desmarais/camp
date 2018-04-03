#!/usr/bin/env python
"""
Creates an HTTP server with basic auth and websocket communication.
"""
import argparse
import base64
import hashlib
import os
import time
import threading
import webbrowser
import datetime as dt

try:
    import cStringIO as io
except ImportError:
    import io

import os, sys, time, subprocess
overlayString = ""

import tornado.web
import tornado.websocket
from tornado.ioloop import PeriodicCallback

# Hashed password for comparison and a cookie for login cache
ROOT = os.path.normpath(os.path.dirname(__file__))
with open(os.path.join(ROOT, "password.txt")) as in_file:
    PASSWORD = in_file.read().strip()
COOKIE_NAME = "camp"


class IndexHandler(tornado.web.RequestHandler):

    def get(self):
        if args.require_login and not self.get_secure_cookie(COOKIE_NAME):
            self.redirect("/login")
        else:
            self.render("index.html", port=args.port)


class LoginHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("login.html")

    def post(self):
        password = self.get_argument("password", "")
        if hashlib.sha512(password).hexdigest() == PASSWORD:
            self.set_secure_cookie(COOKIE_NAME, str(time.time()))
            self.redirect("/")
        else:
            time.sleep(1)
            self.redirect(u"/login?error")


class ErrorHandler(tornado.web.RequestHandler):
    def get(self):
        self.send_error(status_code=403)


class WebSocket(tornado.websocket.WebSocketHandler):
    
    def on_message(self, message):
        """Evaluates the function pointed to by json-rpc."""

        # Start an infinite loop when this is called
        if message == "read_camera":
            if not args.require_login or self.get_secure_cookie(COOKIE_NAME):
                self.camera_loop = PeriodicCallback(self.loop, 10)
                self.camera_loop.start()
            else:
                print("Unauthenticated websocket request")

        # Extensibility for other methods
        else:
            print("Unsupported function: " + message)

    def loop(self):
        def cpu_temp():
            temp = os.popen("vcgencmd measure_temp").readline()
            return (temp.replace("temp=",""))
	"""Sends camera images in an infinite loop."""
        sio = io.StringIO()
	overlayString = ""

	tfile = open("/sys/bus/w1/devices/w1_bus_master1/28-0417837f42ff/w1_slave")
	text1 = tfile.read()
	tfile.close()
	tempdata1 = text1.split()[-1]
	temp1 = float(tempdata1[2:])
	temp1 = temp1 / 1000
	temp1 = '%6.2f'%temp1

	tfile2 = open("/sys/bus/w1/devices/w1_bus_master1/28-0517908cbdff/w1_slave")
	text2 = tfile2.read()
	tfile2.close()
	tempdata2 = text2.split()[-1]
	temp2 = float(tempdata2[2:])
	temp2 = temp2 / 1000
	temp2 = '%6.2f'%temp2

	tfile3 = open("/sys/bus/w1/devices/w1_bus_master1/28-051790b51aff/w1_slave")
	text3 = tfile3.read()
	tfile3.close()
	tempdata3 = text3.split()[-1]
	temp3 = float(tempdata3[2:])
	temp3 = temp3 / 1000
	temp3 = '%6.2f'%temp3

	overlayString += 'BED1'+str(temp1)+'C'
	overlayString += 'ROOM'+str(temp2)+'C'
	overlayString += 'BED2'+str(temp3)+'C'
	overlayString += 'CPU'+str(cpu_temp())

        if args.use_usb:
            _, frame = camera.read()
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img.save(sio, "JPEG")
        else:
            camera.annotate_text_size = 30
            #camera.annotate_text = "I am what I am" 
            #camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.annotate_text = overlayString
	    camera.capture(sio, "jpeg", use_video_port=True)

        try:
            self.write_message(base64.b64encode(sio.getvalue()))
        except tornado.websocket.WebSocketClosedError:
            self.camera_loop.stop()


parser = argparse.ArgumentParser(description="Starts a webserver that "
                                 "connects to a webcam.")
parser.add_argument("--port", type=int, default=8000, help="The "
                    "port on which to serve the website.")
parser.add_argument("--resolution", type=str, default="low", help="The "
                    "video resolution. Can be high, medium, or low.")
parser.add_argument("--require-login", action="store_true", help="Require "
                    "a password to log in to webserver.")
parser.add_argument("--use-usb", action="store_true", help="Use a USB "
                    "webcam instead of the standard Pi camera.")
parser.add_argument("--usb-id", type=int, default=0, help="The "
                     "usb camera number to display")
args = parser.parse_args()

if args.use_usb:
    import cv2
    from PIL import Image
    camera = cv2.VideoCapture(args.usb_id)
else:
    import picamera
    camera = picamera.PiCamera()
    camera.start_preview()

resolutions = {"high": (1280, 720), "medium": (640, 480), "low": (320, 240)}
if args.resolution in resolutions:
    if args.use_usb:
        w, h = resolutions[args.resolution]
        camera.set(3, w)
        camera.set(4, h)
    else:
        camera.resolution = resolutions[args.resolution]
else:
    raise Exception("%s not in resolution options." % args.resolution)

handlers = [(r"/", IndexHandler), (r"/login", LoginHandler),
            (r"/websocket", WebSocket),
            (r"/static/password.txt", ErrorHandler),
            (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': ROOT})]
application = tornado.web.Application(handlers, cookie_secret=PASSWORD)
application.listen(args.port)

webbrowser.open("http://localhost:%d/" % args.port, new=2)

tornado.ioloop.IOLoop.instance().start()
