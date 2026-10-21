from uvicorn import run
from data.initilization.init_db import engine
from data.models.models import Base

def init_db():
    Base.metadata.create_all(bind=engine)


def main():
    init_db()
    run("main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()