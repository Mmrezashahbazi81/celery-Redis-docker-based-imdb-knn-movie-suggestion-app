from flask import Flask, request, jsonify
from database import SessionLocal
from models import Movie
from tasks import add, scrape_movies_task
from classifier import build_classifier, analyze_summary


app = Flask(__name__)

@app.get("/movies")
def get_movies():
    db = SessionLocal()
    movies = db.query(Movie).all()
    return jsonify([{
        "id": m.id,
        "title": m.title,
        "summary": m.summary,
        "rating": m.rating,
        "year": m.year
    } for m in movies])

@app.route("/")
def home():
    return "Welcome to the IMDB API! Try /movies"


@app.post("/scrape")
def scrape_movies():
    limit = int(request.args.get("limit", 250))
    limi = limit
#    scrape_top_movies(limit=limit)
#    return {"message": f"Scraped {limit} movies and saved to DB"}
    result = scrape_movies_task.delay(limi) # ✅ فقط تسک Celery 
    return { 
            "message": f"Scrape task queued for {limit} movies",
            "task_id": result.id
            }


movies, tf_idf_vectors = build_classifier()

@app.post("/predict")
def predict():
    data = request.get_json()
    summary = data.get("summary")
    k = int(data.get("k", 5))
    results = analyze_summary(summary, movies, tf_idf_vectors, k=k)
    return jsonify(results)


@app.route("/test-task")
def test_task():
    result = add.delay(10, 20)
    return jsonify({"task_id": result.id})

if __name__ == "__main__":
    app.run(debug=False)

