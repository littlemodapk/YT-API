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
    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])

        # Pehle try: video+audio ek saath wala mp4
        video = None
        best_h = 0
        for f in formats:
            if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("ext") == "mp4":
                h = f.get("height") or 0
                if h >= best_h:
                    best_h = h
                    video = f["url"]

        # Nahi mila to best video-only mp4 (audio alag se milega)
        if not video:
            best_h = 0
            for f in formats:
                if f.get("vcodec") != "none" and f.get("acodec") == "none" and f.get("ext") == "mp4":
                    h = f.get("height") or 0
                    if h >= best_h:
                        best_h = h
                        video = f["url"]

        audio = None
        best_abr = 0
        for f in formats:
            if f.get("vcodec") == "none" and f.get("acodec") != "none":
                abr = f.get("abr") or 0
                if abr >= best_abr:
                    best_abr = abr
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
