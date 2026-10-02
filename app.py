import os
from flask import Flask, jsonify, request
import yt_dlp

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({"status": True, "message": "YT API running. Use /api?url=VIDEO_LINK"})


@app.route("/api")
def api():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"status": False, "error": "url missing"})

    opts = {"quiet": True, "noplaylist": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])
        video = None
        audio = None
        for f in formats:
            if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("ext") == "mp4":
                video = f["url"]
            if f.get("vcodec") == "none" and f.get("acodec") != "none":
                audio = f["url"]

        return jsonify({
            "status": True,
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "video_url": video,
            "audio_url": audio
        })
    except Exception as e:
        return jsonify({"status": False, "error": str(e)[:300]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
