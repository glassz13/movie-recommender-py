# movie-recommender.py

> tell me one movie you liked. i'll give you exactly 3 like it — no ratings, no trailers, no noise. just trust me. go watch.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-allMiniLM--L6--v2-FF6F00?style=flat)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![HuggingFace](https://img.shields.io/badge/Deployed-HuggingFace-FFD21E?style=flat&logo=huggingface&logoColor=black)

**live demo:** https://glassz13-movie-recommend.hf.space

![demo](demo.gif)

---

## what is this

a content-based movie recommendation system built from scratch. you type a movie you liked, it gives you exactly 3 similar ones based on plot, genre, and keywords — not popularity, not ratings. just semantic similarity.

there's also a random mood-based recommender for when you don't know what you want — pick a mood, get 3 surprise picks.

---

## tech stack

| layer | tool |
|---|---|
| data collection | TMDB API + requests |
| embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| similarity | cosine similarity (sklearn) |
| backend | FastAPI |
| frontend | vanilla HTML/CSS/JS |
| containerization | Docker |
| deployment | Hugging Face Spaces |

---

## how the dataset was built

**source:** TMDB (The Movie Database) public API

scraped two separate pools:
- **Bollywood (Hindi):** 1000 movies, 2000–2025, sorted by popularity
- **Hollywood (English):** 1500 movies, 1995–2025, sorted by popularity

**hard quality gates at collection time** — a movie was skipped if:
- no overview
- overview under 50 characters
- no genres
- no keywords

**post-collection filter:**
- movies with 5+ votes and rating below 4.5 were dropped (removes spam while keeping undiscovered films with no votes)

**final dataset:** ~2300 movies after all filtering

each movie stores: `title, overview, genres, keywords, release_date, vote_average, vote_count, original_language, poster_url, director, top_cast`

---

## recommendation logic

### step 1 — metadata construction

for each movie, a combined text string is built:
```python
overview + genres + genres + keywords + keywords
```

genres and keywords are repeated twice to give them more weight relative to the overview. this matters because overviews are long and would otherwise dominate the semantic space.

### step 2 — embeddings

two separate embedding sets are created using `all-MiniLM-L6-v2`:
- `overview_embeddings` — from overview text only
- `combined_embeddings` — from the full metadata string

embeddings are saved to `embeddings.npz` on first run. subsequent runs load from file — no recomputation needed.

### step 3 — scoring
```python
final_scores = 0.6 * overview_sims + 0.4 * combined_sims
```

- **60% overview similarity** — captures plot and story match
- **40% combined similarity** — captures genre and keyword match

no vote average in the scoring. early experiments showed that including ratings caused high-rated blockbusters (Avatar, Avengers) to dominate results for completely unrelated searches.

### step 4 — language filter

all movies with a different `original_language` than the searched movie are zeroed out before returning results. hindi in → hindi out. english in → english out.

this was critical. without it, hollywood embeddings completely dominated hindi results because english overviews are richer and more detailed in TMDB.

### step 5 — return top 3

---

## random mood recommender

for when you don't know what you want.

1. pick a mood (Action, Comedy, Drama, Thriller, Horror, Sci-Fi)
2. filter all movies matching that genre
3. keep only movies with `vote_average >= 6.0`
4. weighted random sample — weight = `vote_average / sum(vote_averages)`

weighted random means higher rated movies surface more often but results are never deterministic — every click gives different picks.

---

## what works well

hollywood results are strong. TMDB has rich english overviews and dense keyword sets for most english films.

examples:
- `The Dark Knight` → Dark Knight Rises, Joker, Batman Begins
- `Interstellar` → Gravity, Prometheus, 2001: A Space Odyssey
- `Parasite` → Burning, Shoplifters, A Tale of Two Sisters

bollywood military/spy/action films work well due to specific keywords:
- `URI: The Surgical Strike`, `Pathaan`, `Fighter`, `Bell Bottom`

---

## limitations

**bollywood keyword problem**

~48% of Hindi movies on TMDB have empty or sparse keyword sets — keywords are community-contributed and the Hindi section is significantly less maintained. after keyword filtering only ~490 of ~950 Hindi movies remain usable.

broad genre Bollywood films suffer most — `3 Idiots`, `PK`, `Dangal` have generic keywords and weaker results compared to equivalent Hollywood films.

**dataset size**

2300 movies total. after language filtering you're working with ~490 Hindi and ~1800 English movies. for niche genres similarity scores are naturally weaker due to fewer comparable films.

---

## future improvements

- [ ] expand dataset to 10,000+ movies
- [ ] minimum rating threshold on recommendation output
- [ ] switch to `all-mpnet-base-v2` for stronger semantic understanding
- [ ] add more languages (Korean, Spanish, French)
- [ ] user feedback loop to improve results over time

---

## project structure
```
movie-recommender/
├── data_collection.py    # TMDB API scraper — run once to build dataset
├── recommender.py        # embedding + similarity logic
├── main.py               # FastAPI backend
├── tmdb_movies.csv       # final dataset (~2300 movies)
├── embeddings.npz        # saved embeddings (auto-generated on first run)
├── requirements.txt
├── Dockerfile
└── static/
    └── index.html        # frontend
```

---

## run locally
```bash
pip install fastapi uvicorn sentence-transformers scikit-learn pandas numpy
python main.py
```

open `http://localhost:8000`

first run takes 5–10 min to generate embeddings. after that instant.

---

## deployment

deployed on **Hugging Face Spaces** using Docker.
```dockerfile
FROM python:3.9
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /app
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY --chown=user . /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

---

## data source

movie data from [TMDB](https://www.themoviedb.org/). this product uses the TMDB API but is not endorsed or certified by TMDB.
