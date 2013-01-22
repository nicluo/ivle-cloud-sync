from app.database import db_session
from app.models import IVLEFile, User, Job
from app.ivle import IvleClient

class Worker():
    def __init__(self, user):
       self.user = user
       self.client = IvleClient(user.ivle_token)

    def process(self):
       modules = self.client.get('Modules', Duration=0, IncludeAllInfo='false')
       for result in modules['Results']:
           if result['isActive'] == 'Y':
               workbins = self.client.get('Workbins', CourseID=result['ID'], Duration=0)
               for workbin in workbins['Results']:
                   title = workbin['Title']
                   self.exploreFolders(workbin, [title])

    def exploreFolders(self, json, parents):
        for folder in json['Folders']:
            folderName = folder['FolderName']
            for file in folder['Files']:
                fileName = file['FileName']
                fileID = file['ID']
                filePath = '/'.join(parents + [folderName] + [fileName])
                fileURL = self.client.build_download_url(fileID)
                db_session.add(Job(fileID, fileURL, 'http', self.user.user_id,
                    filePath))
                db_session.commit()
            self.exploreFolders(folder, parents + [folderName])

def main():
    for user in User.query.all():
        worker = Worker(user)
        worker.process()

if __name__ == '__main__':
    main()
