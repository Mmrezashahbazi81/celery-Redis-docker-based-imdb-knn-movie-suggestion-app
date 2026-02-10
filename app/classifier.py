import math
import pickle
import redis
import os
from collections import defaultdict, Counter
import spacy
from database import SessionLocal
from models import Movie

# Redis Connection for Caching
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

nlp = spacy.load("en_core_web_sm")

def cleaning(summary):
    doc = nlp(summary)
    words = [w for w in doc if not w.is_stop and not w.is_punct]
    return " ".join(w.text for w in words)

def compute_tf(document):
    word_count = len(document)
    word_freq = Counter(document)
    return {word: count / word_count for word, count in word_freq.items()}

def compute_idf(documents):
    idf_dict = defaultdict(int)
    num_documents = len(documents)
    for doc in documents:
        for word in set(doc):
            idf_dict[word] += 1
    return {word: math.log(num_documents / (count or 1)) + 1 for word, count in idf_dict.items()}

def compute_tf_idf(documents):
    idf_dict = compute_idf(documents)
    tf_idf_documents = []
    for doc in documents:
        tf_dict = compute_tf(doc)
        tf_idf_documents.append({word: tf * idf_dict.get(word, 0) for word, tf in tf_dict.items()})
    return tf_idf_documents

def cosine_similarity(vec1, vec2):
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum(vec1[x] * vec2[x] for x in intersection)
    sum1 = sum(v ** 2 for v in vec1.values())
    sum2 = sum(v ** 2 for v in vec2.values())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    return numerator / denominator if denominator else 0.0

def knn(tf_idf_vectors, new_vector, k=5):
    similarities = [(idx, cosine_similarity(vector, new_vector)) for idx, vector in enumerate(tf_idf_vectors)]
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:k]

def build_and_save_classifier():
    """Triggered by Worker: Rebuilds vectors from DB and saves to Redis"""
    print("[CLASSIFIER] Rebuilding vectors from DB...")
    db = SessionLocal()
    movies_data = db.query(Movie).all()
    if not movies_data:
        db.close()
        return
    
    movie_list = [{"id": m.id, "title": m.title} for m in movies_data]
    summaries = [cleaning(m.summary) for m in movies_data]
    tokenized = [s.split() for s in summaries]
    tf_idf_vectors = compute_tf_idf(tokenized)
    
    data_to_cache = {"movies": movie_list, "vectors": tf_idf_vectors}
    r.set("classifier_data", pickle.dumps(data_to_cache))
    db.close()
    print("[CLASSIFIER] Success: Vectors cached in Redis.")

def analyze_summary(summary, k=5):
    """Triggered by App: Pulls latest data from Redis and predicts"""
    cached_data = r.get("classifier_data")
    if not cached_data:
        return {"error": "No data found. Please run /scrape first."}
    
    data = pickle.loads(cached_data)
    movies = data["movies"]
    tf_idf_vectors = data["vectors"]

    cleaned = cleaning(summary)
    token = cleaned.split()
    
    # Simple TF for the query; in a production system, use the global IDF here.
    tf_new = compute_tf(token)
    
    neighbors = knn(tf_idf_vectors, tf_new, k=k)
    return [{"title": movies[idx]["title"], "similarity": sim} for idx, sim in neighbors]