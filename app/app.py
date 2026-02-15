from classifier import build_and_save_classifier
from flask import Flask, request, jsonify
from tasks import add, scrape_movies_task
from classifier import analyze_summary
from database import SessionLocal, engine
from models import Movie, Base

Base.metadata.create_all(bind=engine)

app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome to the Movie Scraper & KNN API! Use /scrape and /predict."

@app.post("/scrape")
def scrape_movies():
    """
    Endpoint to trigger the background scraping task.
    Usage: POST /scrape?limit=10
    """
    limit = int(request.args.get("limit", 250))
    # Trigger Celery task
    result = scrape_movies_task.delay(limit) 
    
    return { 
        "message": f"Scrape task queued for {limit} movies",
        "task_id": result.id
    }

@app.post("/predict")
def predict():
    """
    Endpoint to find similar movies based on a summary string.
    Body JSON: {"summary": "your text here", "k": 5}
    """
    data = request.get_json()
    summary = data.get("summary")
    if not summary:
        return jsonify({"error": "No summary provided"}), 400
        
    k = int(data.get("k", 5))
    
    # This function pulls the latest vectors from Redis
    results = analyze_summary(summary, k=k)
    
    if isinstance(results, dict) and "error" in results:
        return jsonify(results), 404
        
    return jsonify(results)

@app.get("/movies")
def get_movies():
    """List all movies currently in the database."""
    db = SessionLocal()
    movies = db.query(Movie).all()
    data = [{
        "id": m.id,
        "title": m.title,
        "year": m.year,
        "summary": m.summary[:100] + "..."
    } for m in movies]
    db.close()
    return jsonify(data)

@app.route("/movies", methods=["DELETE"])
def delete_movies():
    try:
        db = SessionLocal()
        num_deleted = db.query(Movie).delete()
        db.commit()
        db.close()
        return {"message": f"Deleted {num_deleted} movies"}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/test-task")
def test_task():
    result = add.delay(10, 20)
    return jsonify({"task_id": result.id})

if __name__ == "__main__":
    # When the app starts, check if we need to build the cache
    print("Checking if NLP cache needs to be initialized...")
    build_and_save_classifier()
    
    # In Docker, we use 0.0.0.0 to be accessible from the host
    app.run(host="0.0.0.0", port=5000, debug=False)
    