# YouTube Shorts Automator

Autonomous YouTube Shorts bot. GitHub Actions creates and uploads Shorts daily at scheduled times.
Zero cost. Zero maintenance once set up.

## Free Tier Usage
| Tool | Free Limit | Your Daily Usage |
|------|-----------|-----------------|
| Gemini 1.5 Flash | 1,500 req/day | 2-3 |
| Pexels API | 20,000 req/month | 2-3 |
| YouTube Data API | 10,000 units/day | ~5,000 |
| edge-tts | Unlimited | — |
| GitHub Actions | Unlimited (public) | ~30 min |

## Configuration
- **Niche**: motivation
- **Schedule**:
- Slot 1: 09:00 (UTC+-5)
- Slot 2: 14:00 (UTC+-5)
- Slot 3: 20:00 (UTC+-5)

## Setup (10 minutes)

### 1. Get API Keys
| Service | URL | Cost |
|---------|-----|------|
| Gemini | https://aistudio.google.com/app/apikey | Free |
| Pexels | https://www.pexels.com/api/ | Free |
| YouTube | Google Cloud Console | Free |

### 2. YouTube Auth (run once on your computer)
```bash
pip install -r requirements.txt
# Save client_secrets.json from Google Cloud first
python setup_auth.py
# Copy the printed JSON to GitHub Secret YOUTUBE_TOKEN_JSON
```

### 3. Add GitHub Secrets
Repo Settings → Secrets and variables → Actions → New secret:
- `GEMINI_API_KEY`
- `PEXELS_API_KEY`
- `YOUTUBE_TOKEN_JSON` (from step 2)
- `DEFAULT_NICHE` = `motivation`

### 4. Test
Actions tab → YouTube Shorts Automator → Run workflow → Run

## How It Works
```
GitHub Actions (cron schedule)
  └── create_short.py
        ├── Gemini Flash  → title + voiceover script + description + tags
        ├── Pexels API    → relevant background stock video (portrait)
        ├── edge-tts      → natural neural voiceover (no key needed)
        ├── FFmpeg        → assembles 1080x1920 Short with title overlay
        └── YouTube API   → uploads as public Short to your channel
```
