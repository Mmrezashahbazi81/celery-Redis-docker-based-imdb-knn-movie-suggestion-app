# 1. ایمپورت‌ها
import jwt
import datetime
from fastapi import Header, HTTPException, status
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional


# این‌ها فایل‌های خودتان هستند که در Flask هم استفاده می‌شوند (کد مشترک)
from database import SessionLocal
from models import Movie
from tasks import scrape_movies_task
from classifier import analyze_summary, build_and_save_classifier

# 2. ساخت اپلیکیشن FastAPI
app = FastAPI(title="Movie Scraper API")

# 3. Dependency Injection برای دیتابیس
# در FastAPI برخلاف Flask که دیتابیس گلوبال است، برای هر درخواست یک سشن جدید می‌سازیم
# و بعد از تمام شدن درخواست، خود FastAPI آن را می‌بندد (yield ... finally db.close())
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. Pydantic Models (Schema Validation)
# این کلاس‌ها "شکل" داده‌های ورودی و خروجی را تعریف می‌کنند.
# مثلاً می‌گوید برای Predict حتما باید summary (متن) و k (عدد) بفرستی.
class PredictRequest(BaseModel):
    summary: str
    k: int = 5  # مقدار پیش‌فرض

# این مدل تعیین می‌کند خروجی API چه شکلی باشد (serializer)
class MovieResponse(BaseModel):
    id: int
    title: str
    year: Optional[int]
    summary: str
    
    # این خط جادویی می‌گوید: "دیتای ورودی اگر از نوع SQLAlchemy بود، خودت تبدیلش کن"
    class Config:
        from_attributes = True

# 5. تعریف مسیرها (Routes)

@app.get("/")
def home():
    # یک پیام متفاوت می‌گذاریم تا بفهمیم الان FastAPI جواب داده
    return "Welcome ... (Powered by FastAPI)"

# در Flask: request.args.get("limit")
# در FastAPI: ورودی تابع (limit: int) اتوماتیک از Query String خوانده می‌شود
@app.post("/scrape")
def scrape_movies(limit: int = Query(250)):
    result = scrape_movies_task.delay(limit)
    return {"message": "Queued", "task_id": result.id}

# اینجا جادوی Pydantic است:
# ورودی request به طور خودکار اعتبارسنجی می‌شود (اگر JSON خراب باشد، خودکار خطا می‌دهد)
@app.post("/predict")
def predict(request: PredictRequest):
    # دسترسی به داده‌ها با . (نقطه) به جای ["key"]
    results = analyze_summary(request.summary, k=request.k)
    
    if isinstance(results, dict) and "error" in results:
        # مدیریت خطا استاندارد FastAPI
        raise HTTPException(status_code=404, detail=results["error"])
        
    return results

# response_model: فرمت خروجی را تضمین می‌کند (لیستی از MovieResponse)
# db: Session = Depends(get_db): سشن دیتابیس را تزریق می‌کند
@app.get("/movies", response_model=List[MovieResponse])
def get_movies(db: Session = Depends(get_db)):
    movies = db.query(Movie).all()
    return movies

# 6. رویداد استارت‌آپ
# این تابع فقط یک بار وقتی سرور روشن می‌شود اجرا می‌شود (مثل if __name__ == main در Flask)
@app.on_event("startup")
def startup_event():
    print("FastAPI Starting: Loading NLP Model...")
    try:
        build_and_save_classifier()
    except Exception as e:
        print(f"Error loading model: {e}")
                
        
# تنظیمات JWT
SECRET_KEY = "super_secret_key_change_me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

class TokenRequest(BaseModel):
    username: str
    password: str  # فعلا دکوری (هر پسوردی قبول است)

# --- 1. اندپوینت لاگین (تولید توکن) ---
@app.post("/auth/token")
def login(creds: TokenRequest):
    # اینجا باید یوزر/پسورد را از دیتابیس چک کنی
    # فعلا برای سادگی هر کسی را قبول می‌کنیم
    if creds.username == "admin" and creds.password == "admin":
        expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {"sub": creds.username, "exp": expiration}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}
    
    raise HTTPException(status_code=400, detail="Incorrect username or password")

# --- 2. اندپوینت اعتبارسنجی (مخصوص Nginx) ---
@app.get("/auth/verify")
def verify_token(authorization: str = Header(None)):
    """
    این تابع توسط Nginx صدا زده می‌شود.
    اگر 200 برگرداند یعنی کاربر مجاز است.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        # اگر بخواهیم یوزرنیم را به سرویس‌های بعدی پاس بدهیم:
        # (Nginx این هدر را می‌گیرد و ست می‌کند)
        return {"status": "ok", "user": username}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")           
