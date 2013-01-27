from app.database import db_session
from app.models import IVLEFile, User, Job, IVLEAnnouncement, IVLEForumHeading
from app.ivle import IvleClient
from datetime import datetime
from time import time


def poll_news_feed(user_id):
    #get server values
    user = User.query.filter(User.user_id == user_id).one()
    client = IvleClient(user.ivle_token)

    modules = client.get('Modules', Duration=0, IncludeAllInfo='false')
    for result in modules['Results']:
        courseCode = result['CourseCode']
        if result['isActive'] == 'Y':
            announcements = client.get('Announcements', CourseID=result['ID'], Duration=0, TitleOnly=False)
            for announcement in announcements['Results']:
                print "---announce---"
                print announcement["ID"]
                print announcement["Title"]
                print announcement["Creator"]["Name"]
                print datetime.fromtimestamp(int(announcement["CreatedDate"][6:16]))
                print announcement["Description"]
                db_session.add(IVLEAnnouncement(announcement, courseCode, user.user_id))
                db_session.commit()
            forums = client.get('Forums', CourseID=result['ID'], Duration=0, IncludeThreads=True, TitleOnly=False)
            print "---forum---"
            for forum in forums['Results']:
                print forum.keys()
                print forum["Title"]
                for heading in forum["Headings"]:
                    print heading.keys()
                    print heading["Title"]
                    new_heading = IVLEForumHeading(forum, heading, courseCode, user.user_id)
                    db_session.add(new_heading)
                    db_session.commit()
                    print new_heading.id
                    for thread in heading["Threads"]:
                        print thread.keys()
                        print thread["ID"]
                        print thread["isNewPost"]
                        print thread["isRead"]
                        print thread["PostTitle"]
                        print thread["Poster"]["Name"]
                        print datetime.fromtimestamp(int(thread["PostDate"][6:16]))
                        print thread["PostBody"]
                        #print thread
                        print thread["Threads"]
            workbins = client.get('Workbins', CourseID=result['ID'], Duration=0)
            for workbin in workbins['Results']:
                title = workbin['Title']
                #self.exploreFolders(workbin, [courseCode + ' ' + title])
        print "------------"


def exploreThreads(self, json, parentID):
    for thread in json['Threads']:
        threadTitle = thread["PostTitle"]
        threadPoster = thread["Poster"]["Name"]
        threadDate = datetime.fromtimestamp(int(thread["PostDate"][6:16]))
        threadBody = thread["PostBody"]


def exploreFolders(self, json, parents):
    for folder in json['Folders']:
        folderName = folder['FolderName']
        for file in folder['Files']:
            fileName = file['FileName']
            fileID = file['ID']
            filePath = '/'.join(parents + [folderName] + [fileName])
            fileURL = self.client.build_download_url(fileID)
            print file
            #db_session.add(Job(fileID, fileURL, 'http', self.user.user_id,
            #    filePath))
            #db_session.commit()
        self.exploreFolders(folder, parents + [folderName])


def exploreAnnouncements(self):
    pass


def exploreForum(self):
    pass

poll_news_feed(1)