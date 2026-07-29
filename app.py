import os
import uuid
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp

app = Flask(__name__)

DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# ডাউনলোডের প্রগ্রেস সেভ রাখার জন্য
progress_db = {}

def progress_hook(d, task_id):
    if d['status'] == 'downloading':
        # পারসেন্টেজ বের করা
        p = d.get('_percent_str', '0%').replace('%', '').strip()
        progress_db[task_id] = p
    elif d['status'] == 'finished':
        progress_db[task_id] = '100'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_info', methods=['POST'])
def get_info():
    url = request.json.get('url')
    ydl_opts = {'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get('title', 'Video'),
                "thumbnail": info.get('thumbnail', '')
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/start_download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    quality = data.get('quality')
    task_id = str(uuid.uuid4())
    
    # ব্যাকগ্রাউন্ডে ডাউনলোড শুরু করার জন্য থ্রেড ব্যবহার
    thread = threading.Thread(target=download_task, args=(url, quality, task_id))
    thread.start()
    
    return jsonify({"task_id": task_id})

def download_task(url, quality, task_id):
    ext = 'mp3' if quality == 'mp3' else 'mp4'
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{task_id}.%(ext)s")
    
    fmt = 'bestvideo[height<=2160]+bestaudio/best' if quality == '4k' else \
          'bestvideo[height<=1080]+bestaudio/best' if quality == '1080' else \
          'bestaudio/best'

    ydl_opts = {
        'format': fmt,
        'outtmpl': output_path,
        'merge_output_format': 'mp4' if quality != 'mp3' else None,
        'progress_hooks': [lambda d: progress_hook(d, task_id)],
        'quiet': True
    }

    if quality == 'mp3':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            progress_db[task_id] = "done" # সফলভাবে শেষ
    except Exception as e:
        progress_db[task_id] = f"error: {str(e)}"

@app.route('/progress/<task_id>')
def get_progress(task_id):
    # ফ্রন্টেন্ড এই রুটে বারবার রিকোয়েস্ট পাঠিয়ে পারসেন্টেজ জানবে
    return jsonify({"progress": progress_db.get(task_id, "0")})

@app.route('/download_file/<task_id>/<quality>')
def download_file(task_id, quality):
    ext = 'mp3' if quality == 'mp3' else 'mp4'
    filename = f"{task_id}.{ext}"
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)