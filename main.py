from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from recommender import df, get_recommendations, format_movie

app = FastAPI(title="Project Z API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")


# ── /recommend ──
@app.get("/recommend")
def recommend(title: str):
    searched, recs = get_recommendations(title)

    if searched is None:
        return {"error": f"'{title}' not found. try another title."}

    return {
        "searched":        format_movie(searched),
        "recommendations": [format_movie(r) for r in recs]
    }


# ── /mood ──
@app.get("/mood")
def mood(genres: str, lang: str = "any"):
    selected_genres = [g.strip().lower() for g in genres.split(",") if g.strip()]

    if not selected_genres:
        return {"error": "pick at least one mood."}

    def matches_mood(movie_genres):
        return any(g in [mg.lower() for mg in movie_genres] for g in selected_genres)

    filtered = df[df["genres"].apply(matches_mood)].copy()

    if lang == "en":
        filtered = filtered[filtered["original_language"] == "en"]
    elif lang == "hi":
        filtered = filtered[filtered["original_language"] == "hi"]

    filtered = filtered[filtered["vote_average"] >= 6.0]

    if len(filtered) < 3:
        return {"error": "not enough movies for this mood. try another."}

    weights = filtered["vote_average"] / filtered["vote_average"].sum()
    picks   = filtered.sample(n=3, weights=weights, random_state=None)

    return {
        "recommendations": [format_movie(picks.loc[i]) for i in picks.index]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)