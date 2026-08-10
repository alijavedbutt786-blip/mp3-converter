import os
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app) # Allows your Hostinger website to connect safely

DOWNLOAD_DIR = "/tmp/downloads" # Render requires saving temp files inside /tmp/
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/convert', methods=['POST'])
def convert_video():
    data = request.get_json() or {}
    video_url = data.get('url', '')

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # Pre-check video length to protect your free server from crashing
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            meta = ydl.extract_info(video_url, download=False)
            if meta.get('duration', 0) > 600: # 10 minutes limit
                return jsonify({"error": "Video is too long! Free server limit is 10 minutes."}), 400
            safe_title = re.sub(r'[^\w\-_\. ]', '', meta.get('title', 'audio'))

        out_template = os.path.join(DOWNLOAD_DIR, f"{safe_title}.%(ext)s")
        final_mp3_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}.mp3")

        # Configuration options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128', # Keeps file sizes small and fast
            }],
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Generate the live download address
        download_link = f"{request.host_url.replace('http://', 'https://')}files/{safe_title}.mp3"
        return jsonify({"mp3_url": download_link})

    except Exception as e:
        return jsonify({"error": f"Failed: {str(e)}"}), 500

@app.route('/files/<filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
