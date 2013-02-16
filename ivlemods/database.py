from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from ivlemods import app

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'],
    convert_unicode=True, echo=app.debug, pool_recycle=3600)
db_session = scoped_session(sessionmaker(autocommit=False,
    autoflush=False,
    bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import ivlemods.models
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)