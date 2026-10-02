import os
import re
import shutil
import requests
from flask import Flask, jsonify, request, Response
import yt_dlp

app = Flask(__name__)

CLIENTS = ["android_vr", "tv", "ios", "mweb", "web_safari"]


@app.after_request
def cors(resp):
    # Blogger / kisi bhi website se call ho sake
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Expose-Headers"] = "Content-Length, Content-Range, Accept-Ranges"
    return resp


def get_cookiefile():
    for src in ("/etc/secrets/cookies.txt", "cookies.txt"):
        if os.path.exists(src):
            dst = "/tmp/cookies.txt"
            shutil.copyfile(src, dst)
            return dst
    return None


def has_video(f):
    return f.get("vcodec") not in (None, "none")


def has_audio(f):
    return f.get("acodec") not in (None, "none")


def is_direct(f):
    return f.get("protocol") in ("https", "http") and f.get("url")


def resolve(url):
    """(info, formats) ya (None, error) return karta hai."""
    cf = get_cookiefile()
    last_err = None
    for client in CLIENTS:
        opts = {
            "quiet": True,
            "noplaylist": True,
            "skip_download": True,
            "extractor_args": {"youtube": {"player_client": [client]}},
        }
        if cf:
            opts["cookiefile"] = cf
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            formats = [f for f in info.get("formats", []) if is_direct(f)]
            if any(has_video(f) for f in formats):
                return info, formats
            last_err = last_err or "no video formats from " + client
        except Exception as e:
            last_err = str(e)
    return None, (last_err or "failed")[:300]


def pick(formats):
    muxed = [f for f in formats if has_video(f) and has_audio(f)]
    muxed.sort(key=lambda f: (f.get("height") or 0, f.get("ext") == "mp4"))
    video = muxed[-1] if muxed else None

    if not video:
        vo = [f for f in formats if has_video(f) and not has_audio(f)]
        vo.sort(key=lambda f: (f.get("ext") == "mp4", f.get("height") or 0))
        video = vo[-1] if vo else None

    aud = [f for f in formats if has_audio(f) and not has_video(f)]
    aud.sort(key=lambda f: (f.get("ext") == "m4a", f.get("abr") or 0))
    audio = aud[-1] if aud else None
    return video, audio


@app.route("/")
def home():
    return jsonify({"status": True, "message": "Use /api?url=LINK, /stream?url=LINK, /download?url=LINK"})


@app.route("/api")
def api():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"status": False, "error": "url missing"})
    info, formats = resolve(url)
    if info is None:
        return jsonify({"status": False, "error": formats})

    video, audio = pick(formats)
    base = request.host_url.rstrip("/")
    from urllib.parse import quote
    q = quote(url, safe="")
    return jsonify({
        "status": True,
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "height": video.get("height") if video else None,
        "video_has_audio": bool(video and has_audio(video)),
        # Ye links browser me chalte hain (server se proxy hoke)
        "stream_url": f"{base}/stream?url={q}",
        "download_url": f"{base}/download?url={q}",
        "audio_stream_url": f"{base}/stream?url={q}&type=audio" if audio else None,
        "audio_download_url": f"{base}/download?url={q}&type=audio" if audio else None,
    })


def proxy(download):
    url = request.args.get("url", "")
    kind = request.args.get("type", "video")
    if not url:
        return jsonify({"status": False, "error": "url missing"}), 400

    info, formats = resolve(url)
    if info is None:
        return jsonify({"status": False, "error": formats}), 502

    video, audio = pick(formats)
    f = audio if kind == "audio" else video
    if not f:
        return jsonify({"status": False, "error": "format not found"}), 404

    headers = {"User-Agent": "Mozilla/5.0"}
    if request.headers.get("Range"):
        headers["Range"] = request.headers["Range"]

    r = requests.get(f["url"], headers=headers, stream=True, timeout=30)

    out = {}
    for k in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
        if r.headers.get(k):
            out[k] = r.headers[k]
    if download:
        name = re.sub(r'[\\/:*?"<>|]', "", info.get("title") or "video")[:80]
        out["Content-Disposition"] = f'attachment; filename="{name}.{f.get("ext") or "mp4"}"'

    def gen():
        for chunk in r.iter_content(chunk_size=64 * 1024):
            if chunk:
                yield chunk

    return Response(gen(), status=r.status_code, headers=out)


@app.route("/stream")
def stream():
    return proxy(download=False)


@app.route("/download")
def download():
    return proxy(download=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
