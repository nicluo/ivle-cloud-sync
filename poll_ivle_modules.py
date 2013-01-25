from app.database import db_session
from app.models import IVLEModule, User
from app.ivle import IvleClient
from datetime import datetime
from time import time


class Worker():
    def __init__(self, user):
        self.user = user
        self.client = IvleClient(user.ivle_token)

    def process(self):
        db_user_modules = IVLEModule.query.filter(IVLEModule.user_id == self.user.user_id).all()
        modules = self.client.get('Modules', Duration=0, IncludeAllInfo='false')

        for result in modules['Results']:
            courseCode = result['CourseCode']
            if result['isActive'] == 'Y':
                #if missing, add module
                db_session.add(IVLEModule(result, self.user.user_id))
                db_session.commit()
                #otherwise, update checked time

def main():
    for user in User.query.all():
        worker = Worker(user)
        worker.process()

if __name__ == '__main__':
    main()