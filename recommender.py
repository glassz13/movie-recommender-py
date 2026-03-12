import ast
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

print("📦 Loading dataset...")
df = pd.read_csv("tmdb_movies.csv")

df["overview"]   = df["overview"].fillna("")
df["genres"]     = df["genres"].apply(ast.literal_eval)
df["keywords"]   = df["keywords"].apply(ast.literal_eval)
df["top_cast"]   = df["top_cast"].apply(ast.literal_eval)
df["director"]   = df["director"].fillna("Unknown")
df["poster_url"] = df["poster_url"].fillna("")
df["release_date"] = df["release_date"].fillna("")

# drop movies with no keywords
df = df[df["keywords"].apply(lambda x: len(x) > 0)].reset_index(drop=True)

def create_metadata(row):
    genres   = " ".join(row["genres"])
    keywords = " ".join(row["keywords"])
    return (
        row["overview"] + " " +
        genres   + " " + genres   + " " +
        keywords + " " + keywords
    )

df["combined_text"] = df.apply(create_metadata, axis=1)

# ── EMBEDDINGS ──
EMBEDDINGS_FILE = "embeddings.npz"
model = SentenceTransformer("all-MiniLM-L6-v2")

if os.path.exists(EMBEDDINGS_FILE):
    print("✅ Loading saved embeddings...")
    data                = np.load(EMBEDDINGS_FILE)
    combined_embeddings = data["combined"]
    overview_embeddings = data["overview"]
else:
    print("🔄 Creating embeddings (one time only)...")
    combined_embeddings = model.encode(
        df["combined_text"].tolist(),
        show_progress_bar=True,
        convert_to_numpy=True
    )
    overview_embeddings = model.encode(
        df["overview"].tolist(),
        show_progress_bar=True,
        convert_to_numpy=True
    )
    np.savez(EMBEDDINGS_FILE, combined=combined_embeddings, overview=overview_embeddings)
    print("✅ Embeddings saved!")

# ── RECOMMENDER ──
def get_recommendations(movie_title: str, top_n: int = 3):
    match = df[df["title"].str.lower() == movie_title.strip().lower()]

    if match.empty:
        match = df[df["title"].str.lower().str.contains(movie_title.strip().lower(), na=False)]
        if match.empty:
            return None, None
        match = match.sort_values("vote_count", ascending=False).head(1)

    base_idx  = match.index[0]
    base_lang = df.loc[base_idx, "original_language"]

    overview_sims = cosine_similarity([overview_embeddings[base_idx]], overview_embeddings)[0]
    combined_sims = cosine_similarity([combined_embeddings[base_idx]], combined_embeddings)[0]

    final_scores = 0.6 * overview_sims + 0.4 * combined_sims

    final_scores[base_idx] = -1

    for i in range(len(df)):
        if df.loc[i, "original_language"] != base_lang:
            final_scores[i] = -1

    top_indices     = np.argsort(final_scores)[::-1][:top_n]
    searched        = df.loc[base_idx]
    recommendations = [df.loc[i] for i in top_indices]

    return searched, recommendations


def format_movie(row):
    return {
        "title":        row["title"],
        "overview":     row["overview"],
        "poster_url":   row["poster_url"],
        "release_date": row["release_date"],
        "genres":       row["genres"],
    }