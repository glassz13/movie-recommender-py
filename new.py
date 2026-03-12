import requests
import pandas as pd
import time

API_KEY = "your-api-key"
BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"

session = requests.Session()


def safe_get(url, retries=5):
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=20)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print("   ⏳ Rate limited. Waiting 15s...")
                time.sleep(15)
            else:
                time.sleep(2)
        except requests.exceptions.RequestException as e:
            wait = (attempt + 1) * 3
            print(f"   ⚠️ Request error: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    return None


def extract_director(credits_data):
    if not credits_data:
        return None
    for member in credits_data.get("crew", []):
        if member.get("job") == "Director":
            return member.get("name")
    return None


def extract_top_cast(credits_data, top_n=5):
    if not credits_data:
        return []
    return [m["name"] for m in credits_data.get("cast", [])[:top_n]]


def fetch_movies(language, total_needed, date_from, date_to):
    movies_data = []
    seen_ids    = set()
    page        = 1
    max_pages   = 500

    while len(movies_data) < total_needed and page <= max_pages:
        print(f"[{language.upper()}] Page {page} | Collected: {len(movies_data)}/{total_needed}")

        url = (
            f"{BASE_URL}/discover/movie"
            f"?api_key={API_KEY}"
            f"&language=en-US"
            f"&with_original_language={language}"
            f"&primary_release_date.gte={date_from}-01-01"
            f"&primary_release_date.lte={date_to}-12-31"
            f"&sort_by=popularity.desc"
            f"&page={page}"
        )

        data = safe_get(url)

        if not data or not data.get("results"):
            print(f"⚠️ No more results for [{language.upper()}] at page {page}. Stopping.")
            break

        if page == 1:
            total_available = data.get("total_results", 0)
            print(f"   TMDB has {total_available} total movies for [{language.upper()}] in {date_from}–{date_to}")

        results = data.get("results", [])
        if not results:
            break

        for movie in results:
            if len(movies_data) >= total_needed:
                break

            movie_id = movie["id"]
            if movie_id in seen_ids:
                continue
            seen_ids.add(movie_id)

            details       = safe_get(f"{BASE_URL}/movie/{movie_id}?api_key={API_KEY}")
            keywords_data = safe_get(f"{BASE_URL}/movie/{movie_id}/keywords?api_key={API_KEY}")
            credits_data  = safe_get(f"{BASE_URL}/movie/{movie_id}/credits?api_key={API_KEY}")

            if not details:
                continue

            # ── hard quality gates ──
            overview = details.get("overview", "").strip()
            genres   = details.get("genres", [])
            keywords = []
            if keywords_data:
                keywords = [kw["name"] for kw in keywords_data.get("keywords", [])]

            if not overview:              continue  # no overview
            if not genres:                continue  # no genres
            if not keywords:              continue  # no keywords — skip trash
            if len(overview) < 50:        continue  # overview too short to be useful

            poster_path = details.get("poster_path")
            poster_url  = f"{POSTER_BASE_URL}{poster_path}" if poster_path else None

            movies_data.append({
                "id":                movie_id,
                "title":             details.get("title"),
                "overview":          overview,
                "genres":            [g["name"] for g in genres],
                "keywords":          keywords,
                "release_date":      details.get("release_date"),
                "vote_average":      details.get("vote_average", 0),
                "vote_count":        details.get("vote_count", 0),
                "original_language": details.get("original_language"),
                "poster_url":        poster_url,
                "director":          extract_director(credits_data),
                "top_cast":          extract_top_cast(credits_data, top_n=5),
            })

            time.sleep(0.3)

        page += 1
        time.sleep(0.5)

    print(f"✅ [{language.upper()}] Collected: {len(movies_data)} movies\n")
    return movies_data


def drop_crap(df):
    before   = len(df)
    has_votes = df["vote_count"] >= 5
    is_crap   = has_votes & (df["vote_average"] < 4.5)
    df        = df[~is_crap].reset_index(drop=True)
    print(f"🗑️  Dropped {before - len(df)} crap movies (5+ votes, rating < 4.5)")
    print(f"✅ Final dataset: {len(df)} movies")
    return df


if __name__ == "__main__":

    print("=" * 50)
    print("Fetching BOLLYWOOD (Hindi) | 2000–2025 | Cap 1000")
    print("=" * 50)
    bollywood = fetch_movies("hi", 1000, "2000", "2025")

    print("=" * 50)
    print("Fetching HOLLYWOOD (English) | 1995–2025 | Cap 1500")
    print("=" * 50)
    hollywood = fetch_movies("en", 1500, "1995", "2025")

    all_movies = bollywood + hollywood
    df = pd.DataFrame(all_movies)
    df = df.drop_duplicates(subset="id").reset_index(drop=True)
    print(f"\n📦 Raw dataset: {len(df)} movies")

    df = drop_crap(df)
    df.to_csv("tmdb_movies.csv", index=False)

    print(f"\n🎬 Done!")
    print(f"   Bollywood : {sum(1 for m in all_movies if m['original_language'] == 'hi')}")
    print(f"   Hollywood : {sum(1 for m in all_movies if m['original_language'] == 'en')}")
    print(f"   Saved to  : tmdb_movies.csv")