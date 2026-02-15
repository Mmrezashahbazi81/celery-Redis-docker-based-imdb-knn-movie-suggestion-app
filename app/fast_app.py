# 1. ایمپورت‌ها (مرتب شده)
import jwt
import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, Header, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

# فایل‌های پروژه
from database import SessionLocal
from models import Movie
from tasks import scrape_movies_task
from classifier import analyze_summary, build_and_save_classifier

# 2. تنظیمات اپلیکیشن و JWT
app = FastAPI(title="Movie Scraper API")

SECRET_KEY = "super_secret_key_change_me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7 

# 3. Pydantic Models
class PredictRequest(BaseModel):
    summary: str
    k: int = 5

class MovieResponse(BaseModel):
    id: int
    title: str
    year: Optional[int]
    summary: str
    class Config:
        from_attributes = True

class TokenRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

# 4. Dependency Injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 5. Helper Functions (توابع کمکی)
def create_tokens(username: str):
    # ساخت Access Token
    access_expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_payload = {"sub": username, "exp": access_expire, "type": "access"}
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)

    # ساخت Refresh Token
    refresh_expire = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_payload = {"sub": username, "exp": refresh_expire, "type": "refresh"}
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": access_token, 
        "refresh_token": refresh_token, 
        "token_type": "bearer"
    }

# 6. رویداد استارت‌آپ
@app.on_event("startup")
def startup_event():
    print("FastAPI Starting: Loading NLP Model...")
    try:
        build_and_save_classifier()
    except Exception as e:
        print(f"Error loading model: {e}")

# ==========================================
#              ROUTES (EndPoints)
# ==========================================

@app.get("/")
def home():
    return "Welcome ... (Powered by FastAPI)"

@app.post("/scrape")
def scrape_movies(limit: int = Query(250)):
    result = scrape_movies_task.delay(limit)
    return {"message": "Queued", "task_id": result.id}

@app.post("/predict")
def predict(request: PredictRequest):
    results = analyze_summary(request.summary, k=request.k)
    if isinstance(results, dict) and "error" in results:
        raise HTTPException(status_code=404, detail=results["error"])
    return results

@app.get("/movies", response_model=List[MovieResponse])
def get_movies(db: Session = Depends(get_db)):
    movies = db.query(Movie).all()
    return movies

# ==========================================
#              AUTH ROUTES
# ==========================================

@app.post("/auth/token")
def login(creds: TokenRequest):
    # چک کردن ساده یوزر/پسورد (در آینده به دیتابیس وصل کنید)
    if creds.username == "admin" and creds.password == "admin":
        return create_tokens(creds.username)
    
    raise HTTPException(status_code=400, detail="Incorrect username or password")

@app.post("/auth/refresh")
def refresh_token(request: RefreshRequest):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        username = payload.get("sub")
        return create_tokens(username)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired. Please login again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# اندپوینت مخصوص Nginx (برای چک کردن توکن)
@app.get("/auth/verify")
def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # اگر توکن Expire شده باشد، اینجا خودش به except jwt.ExpiredSignatureError می‌رود
        if payload.get("type") == "refresh":
             raise HTTPException(status_code=401, detail="Cannot use refresh token for access")

        return {"status": "ok", "user": payload.get("sub")}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
