from ivlemods.database import db_session, init_db
from redis import StrictRedis

init_db()
db_session.commit()
StrictRedis().flushall()