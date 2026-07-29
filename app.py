import os
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp

app = Flask(__name__)

# ডাউনলোড করা ফাইল সাময়িকভাবে রাখার জন্য ফোল্ডার
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

# ভিডিওর তথ্য (Title, Thumbnail) বের করার রুট
@app.route('/get_info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "লিঙ্ক দেওয়া হয়নি"}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get('title', 'Video'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration_string', '0:00')
            })
    except Exception as e:
        return jsonify({"error": "ভিডিওর তথ্য পাওয়া যায়নি। লিঙ্কটি চেক করুন।"}), 500

# ভিডিও ডাউনলোড এবং প্রসেস করার রুট
@app.route('/process_download', methods=['POST'])
def process_download():
    data = request.json
    url = data.get('url')
    quality = data.get('quality') # '4k', '1080', 'mp3'

    if not url:
        return jsonify({"error": "URL missing"}), 400

    # ইউনিক আইডি তৈরি করা যাতে ফাইল ওভারল্যাপ না হয়
    file_id = str(uuid.uuid4())
    ext = 'mp3' if quality == 'mp3' else 'mp4'
    output_filename = f"{file_id}.{ext}"
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.%(ext)s")

    # কোয়ালিটি সেটিংস
    if quality == '4k':
        format_selector = 'bestvideo[height<=2160]+bestaudio/best'
    elif quality == '1080':
        format_selector = 'bestvideo[height<=1080]+bestaudio/best'
    else:
        format_selector = 'bestaudio/best'

    ydl_opts = {
        'format': format_selector,
        'outtmpl': output_path,
        'merge_output_format': 'mp4' if quality != 'mp3' else None,
        'quiet': True,
    }

    # MP3 কনভার্ট করার জন্য সেটিংস
    if quality == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
            # প্রসেস শেষে আসল ফাইলের নাম বের করা
            final_file = f"{file_id}.{ext}"
            return jsonify({"download_url": f"/download_file/{final_file}"})
    except Exception as e:
        return jsonify({"error": "ডাউনলোড ব্যর্থ হয়েছে। আবার চেষ্টা করুন।"}), 500

# ইউজারকে ফাইল সার্ভ করার রুট
@app.route('/download_file/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    # Render বা ইন্টারনেটে হোস্ট করার জন্য host='0.0.0.0' জরুরি
    app.run(host='0.0.0.0', port=5000)
