from app.database import db_session, init_db

init_db()

from app.models import Job

db_session.add_all([
    Job('1000', 'http://www.ics.uci.edu/~bic/courses/JaverOS/pr3.pdf', 'http',
        1, 'CS2106/pr3.pdf'),
    Job('1001',
        'http://ics.uci.edu/~bic/courses/OS-2012/Lectures-on-line/proj3.pptx',
        'http', '1', 'CS2106/proj3.pptx'),
    Job('1000', 'http://www.ics.uci.edu/~bic/courses/JaverOS/pr3.pdf', 'http',
        '1', 'CS2106/hello.pdf')
])
db_session.commit()