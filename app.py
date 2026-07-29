import os
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp

app = Flask(__name__)

DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "লিঙ্ক দেওয়া হয়নি"}), 400

    # ইউটিউব ব্লক এড়ানোর জন্য বিশেষ সেটিংস
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'nocheckcertificate': True,
        'geo_bypass': True,
        'source_address': '0.0.0.0',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'add_header': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # ভিডিওর তথ্য বের করা
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get('title', 'Video'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration_string', '0:00')
            })
    except Exception as e:
        # যদি ইউটিউব ব্লক করে, আমরা অন্যভাবে চেষ্টা করব
        return jsonify({"error": "ইউটিউব আপনার রিকোয়েস্টটি ব্লক করছে। অনুগ্রহ করে ফেসবুক বা টিকটক লিঙ্ক ট্রাই করুন অথবা একটু পর আবার চেষ্টা করুন।"}), 500

@app.route('/process_download', methods=['POST'])
def process_download():
    data = request.json
    url = data.get('url')
    quality = data.get('quality')

    file_id = str(uuid.uuid4())
    ext = 'mp3' if quality == 'mp3' else 'mp4'
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.%(ext)s")

    fmt = 'bestvideo[height<=2160]+bestaudio/best' if quality == '4k' else \
          'bestvideo[height<=1080]+bestaudio/best' if quality == '1080' else \
          'bestaudio/best'

    ydl_opts = {
        'format': fmt,
        'outtmpl': output_path,
        'merge_output_format': 'mp4' if quality != 'mp3' else None,
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
    }

    if quality == 'mp3':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            final_file = f"{file_id}.{ext}"
            return jsonify({"download_url": f"/download_file/{final_file}"})
    except Exception as e:
        return jsonify({"error": "ডাউনলোড ব্যর্থ হয়েছে।"}), 500

@app.route('/download_file/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
