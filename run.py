from flask import Flask, escape, request, render_template, send_from_directory, send_file, Response
import logging
import youtube_dl
import hashlib
import re
import shutil
import json
import os
import io

temporary_dir = "/mnt/myfiles/ytdl_temp"
#temporary_dir = "C:\\ytdl_temp"

app = Flask(__name__)

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
ydl_opts["outtmpl"] = os.path.join(temporary_dir,ydl_opts["outtmpl"])
ydl = youtube_dl.YoutubeDL(ydl_opts)

filecache = {}

if (not os.path.isdir(temporary_dir)):
	os.mkdir(temporary_dir)

for root, path, files in os.walk(temporary_dir):
	for filename in files:
		temp_hash = hashlib.md5(str.encode(filename)).hexdigest()
		filecache[temp_hash] = filename
		print(filename + ": " + temp_hash)

@app.route("/", methods=["GET","POST"])
def hello():
	return render_template("main.html")

@app.route("/run.php", methods=["POST"])
def run():
	data = request.get_json(force=True)
	def generate():
		for i in data:
			m = re.search("youtube.com\/watch\?v=([\w\d\-]+)", i)
			if (m):
				info = ydl.extract_info("https://www.youtube.com/watch?v=" + m.group(1), download=True)
				filename = ydl.prepare_filename(info)
				filename = filename[:filename.rfind(".")] + ".mp3"
				filename = os.path.basename(filename) #Linux has different behaviour, for some reason

				temp_hash = hashlib.md5(str.encode(filename)).hexdigest()
				filecache[temp_hash] = filename

				yield "/download/" + temp_hash #See if you cant abuse partial content

	return Response(generate())

@app.route("/download/<hash>")
def download(hash):
	if (hash in filecache):
		filename = filecache.pop(hash)
		filepath = os.path.join(temporary_dir, filename)

		return_data = io.BytesIO()
		with open(filepath, 'rb') as fo:
			return_data.write(fo.read())
		# (after writing, cursor will be at last byte, so move it to start)
		return_data.seek(0)

		os.remove(filepath)

		logging.info("Filename: " + filename)
		return send_file(return_data,
			mimetype="audio/mpeg",
			attachment_filename=filename,
			as_attachment=True,
		)
	else:
		return "Lol no"

logging.basicConfig(level=logging.INFO)
if __name__ == "__main__":
	app.run()
