from flask import Flask, request, jsonify, render_template, Response, send_file
from flask_cors import CORS
from flask import after_this_request
import yt_dlp
import requests
import os
import subprocess
import traceback
from tempfile import NamedTemporaryFile, mkdtemp
import shutil

app = Flask(__name__, template_folder="public")
CORS(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("https://iky.pythonanywhere.com/api/fetch-info", methods=["POST"])
def fetch_info():
    url = request.json.get("url")
    if not url:
        return jsonify({"error": "URL tidak ditemukan"}), 400

    try:
        # Perbaikan: Tambahkan opsi untuk mengatasi masalah YouTube bot detection
        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            # Gunakan cookies dari browser
            "extractor_args": {
                "youtube": {
                    "skip": ["dash", "hls"]  # Skip format yang mungkin bermasalah
                }
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            formats_to_send = []
            for f in info.get("formats", []):
                if f.get("url"):
                    title = info.get("title", "video")
                    encoded_title = (
                        title.replace('"', "").replace("'", "").replace(" ", "_")
                    )

                    if (
                        f.get("vcodec") != "none"
                        and f.get("acodec") != "none"
                        and f.get("ext") == "mp4"
                    ):
                        formats_to_send.append(
                            {
                                "resolution": f.get("format_note", "N/A"),
                                "ext": "mp4",
                                "download_url": f"/download-mp4?url={url}&filename={encoded_title}.mp4",
                                "filesize_approx": f.get("filesize")
                                or f.get("filesize_approx", 0),
                            }
                        )
                    elif f.get("vcodec") == "none" and f.get("acodec") != "none":
                        is_audio_added = any(
                            item["ext"] == "mp3" for item in formats_to_send
                        )
                        if not is_audio_added:
                            formats_to_send.append(
                                {
                                    "resolution": f"{f.get('abr', 0)}k",
                                    "ext": "mp3",
                                    "download_url": f"/download-mp3?url={url}&filename={encoded_title}.mp3",
                                    "filesize_approx": f.get("filesize")
                                    or f.get("filesize_approx", 0),
                                }
                            )

            video_data = {
                "title": info.get("title", "Tanpa Judul"),
                "thumbnail": info.get("thumbnail"),
                "formats": formats_to_send,
                "original_url": url,
            }
            return jsonify(video_data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan pada server: {str(e)}"}), 500

@app.route("/download-mp4")
def download_mp4():
    url = request.args.get("url")
    filename = request.args.get("filename", "video.mp4")

    try:
        temp_output = NamedTemporaryFile(delete=False, suffix=".mp4")
        output_path = temp_output.name
        temp_output.close()  # Hindari file locking

        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": output_path,
            "quiet": True,
            "merge_output_format": "mp4",
            "ffmpeg_location": "D:/ffmpeg/bin/ffmpeg.exe"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        @after_this_request
        def cleanup(response):
            try:
                os.remove(output_path)
            except Exception as e:
                print(f"Gagal menghapus file: {e}")
            return response

        return send_file(output_path, as_attachment=True, download_name=filename, mimetype="video/mp4")

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Gagal mengunduh file: {str(e)}"}), 500

@app.route("/download-mp3")
def download_mp3():
    url = request.args.get("url")
    filename = request.args.get("filename", "audio.mp3")

    try:
        # Perbaikan: Buat direktori temporary dan gunakan nama file yang eksplisit
        temp_dir = mkdtemp()
        temp_filename = os.path.join(
            temp_dir, "audio"
        )  # Tanpa ekstensi, biarkan yt-dlp menambahkan

        # Perbaikan: Tambahkan opsi untuk mengatasi masalah YouTube bot detection
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": temp_filename + ".%(ext)s",
            "quiet": True,
            "cookiefile": None,  # Jangan pakai cookies dari browser
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Cari file MP3 yang dihasilkan
        mp3_file = temp_filename + ".mp3"
        if not os.path.exists(mp3_file):
            # Coba cari file dengan ekstensi lain yang mungkin dikonversi
            for ext in [".mp3", ".m4a", ".webm", ".ogg"]:
                potential_file = temp_filename + ext
                if os.path.exists(potential_file):
                    mp3_file = potential_file
                    break

        if not os.path.exists(mp3_file):
            raise FileNotFoundError("File audio tidak ditemukan setelah konversi")

        # Perbaikan: Gunakan send_file untuk mengirim file dengan benar
        def remove_file(response):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            return response

        return send_file(
            mp3_file, as_attachment=True, download_name=filename, mimetype="audio/mpeg"
        )

    except Exception as e:
        traceback.print_exc()
        # Bersihkan direktori temporary jika terjadi error
        try:
            if "temp_dir" in locals():
                shutil.rmtree(temp_dir)
        except:
            pass
        return jsonify({"error": f"Gagal mengonversi audio: {str(e)}"}), 500
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5500))
    app.run(debug=False, host="0.0.0.0", port=port)
