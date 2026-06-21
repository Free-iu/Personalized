#!/usr/bin/env python3
"""
create_short.py - YouTube Shorts Automator
===================================================
100% Free Stack:
  Gemini 1.5 Flash  -> 1,500 req/day free (no CC)
  Pexels API        -> 20,000 req/month free (no CC)
  edge-tts          -> unlimited free, no key needed
  FFmpeg            -> open source, pre-installed on GitHub
  YouTube API v3    -> 10,000 units/day free (~6 uploads)
===================================================
"""

import os, sys, json, asyncio, subprocess, re, time, tempfile
from pathlib import Path
import requests

GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "")
PEXELS_KEY  = os.environ.get("PEXELS_API_KEY", "")
YT_CREDS    = os.environ.get("YOUTUBE_TOKEN_JSON", "")
NICHE       = os.environ.get("NICHE", "motivation")
VOICE       = os.environ.get("VOICE", "en-US-GuyNeural")
MAX_SEC     = 58  # Shorts must be < 60 seconds


# ── 1. GENERATE CONTENT (Gemini 1.5 Flash) ──────────────────────────────────
def generate_content(niche):
    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        "/models/gemini-1.5-flash:generateContent?key=" + GEMINI_KEY
    )
    prompt = (
        f'You are a viral YouTube Shorts creator. '
        f'Create content for the "{niche}" niche.\n\n'
        'Return ONLY valid JSON (no markdown):\n'
        '{\n'
        '  "title": "Hook-driven title under 60 chars",\n'
        '  "script": "Voiceover 110-130 words. Strong hook. Real value. CTA at end.",\n'
        '  "description": "3-4 sentence description + 5 hashtags including #Shorts",\n'
        '  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8"],\n'
        '  "pexels_keyword": "2-3 word Pexels video search term"\n'
        '}'
    )
    r = requests.post(
        url,
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1024}},
        timeout=30
    )
    r.raise_for_status()
    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Strip markdown code fences if Gemini wraps the response
    lines = raw.split("\n")
    start = next((i for i, l in enumerate(lines) if l.strip().startswith("{")), 0)
    rev   = list(reversed(lines))
    end   = len(lines) - 1 - next((i for i, l in enumerate(rev) if l.strip().endswith("}")), 0)
    raw   = "\n".join(lines[start:end + 1])
    return json.loads(raw)


# ── 2. FETCH BACKGROUND VIDEO (Pexels) ──────────────────────────────────────
def get_video(keyword, output):
    headers = {"Authorization": PEXELS_KEY}
    for orientation in ("portrait", "landscape"):
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params={"query": keyword, "orientation": orientation,
                    "per_page": 10, "size": "medium"},
            timeout=30
        )
        if r.status_code != 200:
            continue
        for video in r.json().get("videos", [])[:5]:
            files = sorted(video["video_files"],
                           key=lambda x: x.get("height", 0), reverse=True)
            for f in files:
                if f.get("file_type") == "video/mp4":
                    print(f"  Found: {video['id']} ({f.get('width')}x{f.get('height')})")
                    dl = requests.get(f["link"], stream=True, timeout=120)
                    with open(output, "wb") as fp:
                        for chunk in dl.iter_content(8192):
                            fp.write(chunk)
                    return True
    return False


# ── 3. CREATE VOICEOVER (edge-tts, no API key) ───────────────────────────────
async def make_voiceover(script, voice, output):
    import edge_tts
    await edge_tts.Communicate(script, voice).save(output)


# ── 4. BUILD THE SHORT (FFmpeg) ──────────────────────────────────────────────
def build_short(bg, vo, title, output):
    # Get voiceover duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", vo],
        capture_output=True, text=True, check=True
    )
    dur = min(float(json.loads(probe.stdout)["format"]["duration"]) + 0.3, MAX_SEC)

    # Clean title for FFmpeg drawtext (remove shell-problematic chars)
    import re as _re
    safe_title = _re.sub(r"[':=%@#]", "", title)[:55]

    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "format=yuv420p,"
        f"drawtext=text='{safe_title}':"
        "fontsize=48:fontcolor=white:"
        "x=(w-text_w)/2:y=100:"
        "box=1:boxcolor=black@0.65:boxborderw=16:"
        "fontweight=bold"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", bg,
        "-i", vo,
        "-t", str(dur),
        "-vf", vf,
        "-af", "loudnorm",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        output
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("FFmpeg failed:\n" + res.stderr[-600:])
    print(f"  Video: {Path(output).stat().st_size / 1024 / 1024:.1f} MB, {dur:.1f}s")


# ── 5. UPLOAD TO YOUTUBE (Data API v3) ──────────────────────────────────────
def upload_to_youtube(path, title, description, tags):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GReq

    d = json.loads(YT_CREDS)
    creds = Credentials(
        token=d.get("token"),
        refresh_token=d.get("refresh_token"),
        token_uri=d.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=d.get("client_id"),
        client_secret=d.get("client_secret"),
        scopes=d.get("scopes", ["https://www.googleapis.com/auth/youtube.upload"])
    )
    if not creds.valid:
        creds.refresh(GReq())

    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {
            "title": title[:100],
            "description": description + "\n\n#Shorts",
            "tags": tags,
            "categoryId": "22",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    media = MediaFileUpload(path, mimetype="video/mp4", resumable=True, chunksize=1024 * 1024)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  Uploading: {int(status.progress() * 100)}%")
    return resp["id"]


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("\n🎬 YouTube Shorts Automator")
    print(f"📌 Niche: {NICHE}  |  Voice: {VOICE}")
    print(f"🕐 {time.strftime('%Y-%m-%d %H:%M UTC')}\n")

    missing = [k for k in ("GEMINI_API_KEY", "PEXELS_API_KEY", "YOUTUBE_TOKEN_JSON")
               if not os.environ.get(k)]
    if missing:
        print("❌ Missing GitHub Secrets:", ", ".join(missing))
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        bg  = f"{tmp}/bg.mp4"
        vo  = f"{tmp}/vo.mp3"
        out = f"{tmp}/short.mp4"

        print("1️⃣  Generating content with Gemini Flash...")
        c = generate_content(NICHE)
        print(f"   Title:   {c['title']}")
        print(f"   Keyword: {c['pexels_keyword']}")

        print("2️⃣  Fetching background video from Pexels...")
        if not get_video(c["pexels_keyword"], bg):
            print(f"   Retrying with niche keyword: {NICHE}")
            if not get_video(NICHE, bg):
                print("   ❌ No video found. Check PEXELS_API_KEY.")
                sys.exit(1)

        print("3️⃣  Creating voiceover with edge-tts...")
        asyncio.run(make_voiceover(c["script"], VOICE, vo))

        print("4️⃣  Assembling Short with FFmpeg...")
        build_short(bg, vo, c["title"], out)

        print("5️⃣  Uploading to YouTube...")
        vid_id = upload_to_youtube(out, c["title"], c["description"], c.get("tags", []))

        print("\n✅ SUCCESS!")
        print(f"   Title : {c['title']}")
        print(f"   URL   : https://www.youtube.com/shorts/{vid_id}")


if __name__ == "__main__":
    main()
