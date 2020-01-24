#!/usr/bin/env python3
"""
Very simple HTTP server in python for logging requests
Usage::
	./server.py [<port>]
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import youtube_dl
import hashlib
import shutil
import json
import os

temporary_dir = "temp"

ydl_opts = {
	'format': 'bestaudio/best',
	'postprocessors': [{
		'key': 'FFmpegExtractAudio',
		'preferredcodec': 'mp3',
	}],
	'prefer_ffmpeg': True,
	'keepvideo': False,
	'outtmpl': '%(title)s.%(ext)s'
}
ydl = None

filecache = {}
class S(BaseHTTPRequestHandler):
	def _set_response(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()

	def do_GET(self):
		logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
		if (self.path == "/"):
			# Send the html message
			self._set_response()
			with open("main.html", "r") as file_object:
				self.wfile.write(file_object.read().encode("utf8"))
			
		if (self.path == "/favicon.ico"):
			self.send_response(404)

		if (self.path.startswith("/download/")):
			temp_hash = self.path[len("/download/"):]
			if (temp_hash in filecache):
				filename = filecache.pop(temp_hash)

				with open(filename, 'rb') as file:
					self.send_response(200)
					self.send_header('Content-Type', 'audio/mp3')
					self.send_header('Content-Disposition', 'attachment; filename=\"%s\"' % os.path.basename(filename))
					fs = os.fstat(file.fileno())
					self.send_header("Content-Length", str(fs.st_size))
					self.end_headers()
					shutil.copyfileobj(file, self.wfile)

				os.remove(filename)
			else:
				self.send_response(404)

	def do_POST(self):
		content_length = int(self.headers["Content-Length"]) # <--- Gets the size of data
		post_data = self.rfile.read(content_length) # <--- Gets the data itself
		body_data = post_data.decode("utf-8")
		logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n", str(self.path), str(self.headers), body_data)
		if (self.path == "/run.php"):
			lst = []
			for i in body_data.split("\n"):
				if (not i):
					continue

				try:
					info = ydl.extract_info(i, download=True)
					filename = ydl.prepare_filename(info)
					filename = filename[:filename.rfind(".")] + ".mp3"

					temp_hash = hashlib.md5(str.encode(filename)).hexdigest()
					filecache[temp_hash] = filename

					lst.append("/download/" + temp_hash) #See if you cant abuse partial content
				except Exception:
					self.send_response(400)
					self.end_headers()
					return
			
			response = json.dumps(lst).encode("utf-8")
			self.send_response(200)
			self.send_header("Content-Length", str(len(response)))
			self.end_headers()
			self.wfile.write(response)


def run(server_class=HTTPServer, handler_class=S, port=8080, tmp_dir="temp"):
	global ydl
	global ydl_opts
	global temporary_dir

	logging.basicConfig(level=logging.INFO)
	server_address = ('', port)
	httpd = server_class(server_address, handler_class)
	logging.info("Starting httpd...\n")
	
	temporary_dir = tmp_dir
	try:
		os.mkdir(temporary_dir)
	except Exception:
		pass

	ydl_opts["outtmpl"] = os.path.join(temporary_dir,ydl_opts["outtmpl"])
	ydl = youtube_dl.YoutubeDL(ydl_opts)

	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		pass
	httpd.server_close()
	logging.info("Stopping httpd...\n")
	#ydl.close()

if __name__ == "__main__":
	from sys import argv

	if len(argv) == 3:
		run(port=int(argv[1]),tmp_dir=str(argv[2]))
	else:
		run()
