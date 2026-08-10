import os
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


# CRUCIAL FIX: This forces Render to create the temp folders cleanly at startup
DOWNLOAD_DIR = "/tmp/downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/convert', methods=['POST'])
def convert_video():
    data = request.get_json() or {}
    video_url = data.get('url', '')

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # Pre-check video metadata
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            meta = ydl.extract_info(video_url, download=False)
            if meta.get('duration', 0) > 600:
                return jsonify({"error": "Video too long! 10 mins max."}), 400
            safe_title = re.sub(r'[^\w\-_\. ]', '', meta.get('title', 'audio'))

        out_template = os.path.join(DOWNLOAD_DIR, f"{safe_title}.%(ext)s")
        final_mp3_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}.mp3")

                # Upgraded options to bypass YouTube bot detection firewalls
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
        }

            'quiet': True
        }

        # Clear file if it already exists to save free space
        if os.path.exists(final_mp3_path):
            os.remove(final_mp3_path)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Formulate the response download address link
        host_url = request.host_url.replace('http://', 'https://')
        download_link = f"{host_url}files/{safe_title}.mp3"
        return jsonify({"mp3_url": download_link})

    except Exception as e:
        return jsonify({"error": f"Failed: {str(e)}"}), 500

@app.route('/files/<filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    # Default Render port assignment fallback
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
