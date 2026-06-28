# 🎬 CineLog

<div dir="rtl">

## یه توضیح کوتاه برای فارسی زبانان

این یه ابزار شخصیه برای اینکه بدونی چی دیدی، چی داری می‌بینی، و چی باید ببینی بعدش.

فیلم/سریال رو سرچ می‌کنی (مستقیم از TMDB، با پوستر و خلاصه‌ی واقعی)، به لیستت اضافه می‌کنی، وضعیتش رو مشخص می‌کنی (می‌خوام ببینم / در حال دیدن / دیدم)، و اگه دیدیش یه امتیاز از ۱ تا ۱۰ بهش می‌دی.

بعد از چندتا امتیاز، دکمه‌ی **"Suggest What's Next"** رو می‌زنی — یه هوش مصنوعی (Groq/Llama) به امتیازهای قبلیت نگاه می‌کنه، می‌فهمه چه ژانرهایی رو بیشتر دوست داری، و چندتا فیلم/سریال **واقعی** پیشنهاد می‌ده، همراه با توضیح اینکه چرا فکر می‌کند بهت می‌خوره.

نکته‌ی مهم: AI فقط *پیشنهاد* می‌ده، ولی قبل از نشون دادن به تو، هر پیشنهاد رو با TMDB چک می‌کنیم تا مطمئن شیم واقعاً وجود دارد — چون مدل‌های زبانی گاهی اسم فیلم الکی می‌سازن! اگه یه پیشنهاد در TMDB پیدا نشه، خودکار حذف می‌شه و نشونت داده نمی‌شه.

برای کار کردنش به دو چیز نیاز داری (هر دو رایگان):
- **TMDB API Key** — برای جستجوی فیلم/سریال (بدون این، اصل کار نمی‌کند)
- **Groq API Key** — فقط برای بخش پیشنهاد AI    (بدونش هم لیست و امتیازدهی کار می‌کند، فقط دکمه‌ی پیشنهاد غیرفعال می‌مونه)

راهنمای گرفتن این دو تا کلید در ادامه متن هست.

</div>

---

A personal movie & TV watchlist tracker that learns your taste — and tells you what to watch next.

CineLog lets you search real movies and shows (via TMDB), track what you've watched/are watching/want to watch, rate what you've seen, and then get AI-generated recommendations that are **verified against real TMDB data** — so the AI never gets to invent a title that doesn't exist.

Built with **FastAPI** + **SQLite**, powered by **TMDB** for movie/TV data and **Groq (Llama 3.3)** for taste analysis.

---

## ✨ Features

- **Real movie/TV search** — live search against The Movie Database (TMDB), with posters, overviews, and genres
- **Three-state tracking** — Want to Watch / Watching / Watched, with 1–10 ratings for anything you've seen
- **AI recommendations with real explanations** — analyzes your rating history by genre, then asks an LLM for specific suggestions with a reason tied to *your actual ratings*, not generic blurbs
- **AI suggestions are verified, not trusted blindly** — every AI-suggested title is looked up on TMDB before being shown; if the model invents something that doesn't exist, it's silently filtered out
- **Duplicate protection** — can't accidentally add the same title twice
- **Zero-cost AI layer** — runs on Groq's free tier (search and tracking work even with no AI key at all)

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI |
| Database | SQLite via SQLAlchemy |
| Movie/TV data | TMDB API (`/search/multi`, `/movie/{id}`, `/tv/{id}`) |
| Taste analysis & suggestions | Groq (Llama 3.3 70B Versatile) |
| Frontend | Plain HTML/CSS/JS (no build step) |

---

## 📁 Project Structure

```
cinelog/
├── app.py                  # FastAPI routes
├── tmdb_client.py           # TMDB API wrapper (search, details, normalization)
├── recommender.py            # Taste analysis + AI suggestion + TMDB verification
├── database.py                 # SQLAlchemy models (SQLite)
├── models.py                    # Pydantic request/response schemas
├── config.py
├── static/
│   └── index.html               # Single-page web app
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get a free TMDB API key (required for search)

1. Sign up at [themoviedb.org/signup](https://www.themoviedb.org/signup) and verify your email
2. Go to [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
3. Click **Request an API Key** → choose **Developer** → fill in basic details (any app name/URL works, e.g. `http://localhost`)
4. Copy the **API Key (v3)**

### 3. Get a free Groq API key (optional — only needed for AI recommendations)

Get one at [console.groq.com/keys](https://console.groq.com/keys).

### 4. Configure `.env`

```bash
cp .env.example .env
```

Paste your `TMDB_API_KEY` (and `GROQ_API_KEY` if you want recommendations) into `.env`.

### 5. Run the app

```bash
uvicorn app:app --reload
```

Open **http://127.0.0.1:8000** in your browser — go to that URL directly; don't double-click `static/index.html`, since the page needs to be served by the backend to reach the API.

### 6. Use it

1. Search for a movie or show, click **+ Add**
2. Use the dropdown on each poster card to update its status, and the rating field once you've watched it
3. Rate at least 3 titles as "Watched", then click **✨ Get AI Recommendations**

---

## 📡 API Reference

### `GET /api/search?q=inception`
Searches TMDB for movies and TV shows.

### `POST /api/watchlist`
```json
{ "tmdb_id": 27205, "media_type": "movie", "status": "want_to_watch" }
```

### `GET /api/watchlist?status=watched`
Lists your watchlist, optionally filtered by status.

### `PATCH /api/watchlist/{id}`
```json
{ "status": "watched", "user_rating": 9 }
```

### `DELETE /api/watchlist/{id}`

### `GET /api/recommend`
Analyzes your rated "watched" items and returns AI-suggested titles, each verified to exist on TMDB:

```json
{
  "based_on_summary": "You strongly favor sci-fi and action with high ratings...",
  "recommendations": [
    {
      "title": "Interstellar",
      "media_type": "movie",
      "release_year": "2014",
      "reason": "Like Inception and The Matrix, this is high-concept sci-fi you've rated highly before."
    }
  ]
}
```

---

## 🧠 How the recommendation pipeline works

1. **Aggregate**: your rated "watched" items are grouped by genre, with an average rating per genre, to build a compact taste profile
2. **Suggest**: that profile (plus titles you already have, to exclude) is sent to the LLM, which proposes specific real-sounding titles with a reason for each
3. **Verify**: each suggested title is looked up on TMDB by exact search. If TMDB can't find a confident match, that suggestion is dropped — the AI proposes, TMDB confirms

This two-step design means the AI is never the final source of truth on what exists; it only ever influences which *real, TMDB-verified* titles get suggested.

---

## ⚠️ Limitations

- Recommendation quality depends on having a reasonably diverse rated history — 3 ratings is the technical minimum, but more (10+) gives the AI much more to work with.
- TMDB verification matches on title text; very obscure or recently-renamed titles might occasionally fail to match even if they do exist.
- This project uses TMDB's free API for non-commercial use — see [TMDB's terms](https://www.themoviedb.org/documentation/api/terms-of-use) if you intend to use this beyond a personal/portfolio project.
- No user accounts — this is a single-user local tool as built (see Next Steps).

---

## 🗺 Possible Next Steps

- [ ] Multi-user support with authentication
- [ ] "Why didn't you like this" feedback loop to refine future recommendations
- [ ] Trakt.tv or Letterboxd import for an instant taste profile
- [ ] Episode-level tracking for TV shows (not just whole-series status)
- [ ] Dockerize for one-command deployment

---

## 📄 License

MIT — free to use, modify, and build on. This product uses the TMDB API but is not endorsed or certified by TMDB.

Mohammad Mahdi Mohammadi

