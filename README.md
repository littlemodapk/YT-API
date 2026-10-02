# YouTube Info API (Vercel)

## Deploy steps
1. GitHub par naya repo banao (jaise `yt-api`)
2. Is poore folder ka content us repo me upload/push karo
3. vercel.com par GitHub se login karo
4. "Add New Project" -> apna repo chuno -> Deploy
5. Deploy hone ke baad URL milega: https://aapka-app.vercel.app/api?url=https://youtu.be/xxxx

## Local test (optional)
```
pip install -r requirements.txt
python -c "from api.index import app; app.run(port=5000)"
```
Browser me kholo: http://localhost:5000/api?url=https://youtu.be/dQw4w9WgXcQ

## Dhyan rakho
- YouTube cloud IPs (Vercel/Render/etc) ko kabhi-kabhi block karta hai ("Sign in to confirm you're not a bot"). Agar ye ho to Render ya apna VPS try karo.
- Bina ffmpeg ke video+audio ek saath sirf 360p tak milta hai.
- yt-dlp ko regularly update karte raho (`pip install -U yt-dlp`), YouTube apna system badalta rehta hai.
