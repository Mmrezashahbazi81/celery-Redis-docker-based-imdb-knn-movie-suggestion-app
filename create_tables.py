from database import Base, engine
from models import Movie

Base.metadata.create_all(bind=engine)
