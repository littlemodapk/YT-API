import os
from flask import Flask, jsonify, request
import yt_dlp

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({"status": True, "message": "YT API running. Use /api?url=VIDEO_LINK  (debug: &debug=1)"})


def has_video(f):
    return f.get("vcodec") not in (None, "none")


def has_audio(f):
    return f.get("acodec") not in (None, "none")


def is_direct(f):
    # m3u8 / dash manifest / storyboard (mhtml) nahi chahiye, sirf direct https link
    return f.get("protocol") in ("https", "http") and f.get("url")


@app.route("/api")
def api():
    url = request.args.get("url", "")
    debug = request.args.get("debug")
    if not url:
        return jsonify({"status": False, "error": "url missing"})

    opts = {
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
        # Ye clients JS/PO-token ke bina bhi video formats dete hain
        "extractor_args": {"youtube": {"player_client": ["android_vr", "tv", "web_safari", "web"]}},
    }
    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = [f for f in info.get("formats", []) if is_direct(f)]

        if debug:
            return jsonify({
                "status": True,
                "formats": [
                    {
                        "id": f.get("format_id"),
                        "ext": f.get("ext"),
                        "h": f.get("height"),
                        "v": f.get("vcodec"),
                        "a": f.get("acodec"),
                        "proto": f.get("protocol"),
                    }
                    for f in formats
                ],
            })

        # 1) video + audio ek saath (progressive) - best height
        muxed = [f for f in formats if has_video(f) and has_audio(f)]
        muxed.sort(key=lambda f: (f.get("height") or 0, f.get("ext") == "mp4"))
        video = muxed[-1]["url"] if muxed else None
        video_has_audio = bool(video)

        # 2) nahi mila to video-only (mp4 prefer)
        video_only = [f for f in formats if has_video(f) and not has_audio(f)]
        video_only.sort(key=lambda f: (f.get("ext") == "mp4", f.get("height") or 0))
        video_only_url = video_only[-1]["url"] if video_only else None
        if not video:
            video = video_only_url

        # audio (m4a prefer)
        audios = [f for f in formats if has_audio(f) and not has_video(f)]
        audios.sort(key=lambda f: (f.get("ext") == "m4a", f.get("abr") or 0))
        audio = audios[-1]["url"] if audios else None

        return jsonify({
            "status": True,
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "video_url": video,
            "video_has_audio": video_has_audio,
            "audio_url": audio,
        })
    except Exception as e:
        return jsonify({"status": False, "error": str(e)[:300]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
