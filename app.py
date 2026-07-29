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

    # শক্তিশালী অপশন যা ব্লক এড়াতে সাহায্য করে
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'no_color': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # সরাসরি তথ্য বের করা
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("No info found")
                
            return jsonify({
                "title": info.get('title', 'Video'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration_string', '0:00')
            })
    except Exception as e:
        print(f"Error: {str(e)}") # এটি Render Logs-এ দেখা যাবে
        return jsonify({"error": f"সার্ভার ভিডিওটি খুঁজে পাচ্ছে না। একটু পর আবার চেষ্টা করুন বা অন্য লিঙ্ক দিন।"}), 500

@app.route('/process_download', methods=['POST'])
def process_download():
    data = request.json
    url = data.get('url')
    quality = data.get('quality')

    file_id = str(uuid.uuid4())
    ext = 'mp3' if quality == 'mp3' else 'mp4'
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.%(ext)s")

    if quality == '4k':
        fmt = 'bestvideo[height<=2160]+bestaudio/best'
    elif quality == '1080':
        fmt = 'bestvideo[height<=1080]+bestaudio/best'
    else:
        fmt = 'bestaudio/best'

    ydl_opts = {
        'format': fmt,
        'outtmpl': output_path,
        'merge_output_format': 'mp4' if quality != 'mp3' else None,
        'quiet': True,
        'nocheckcertificate': True
    }

    if quality == 'mp3':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            final_file = f"{file_id}.{ext}"
            return jsonify({"download_url": f"/download_file/{final_file}"})
    except Exception as e:
        return jsonify({"error": "ডাউনলোড করা সম্ভব হচ্ছে না।"}), 500

@app.route('/download_file/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
