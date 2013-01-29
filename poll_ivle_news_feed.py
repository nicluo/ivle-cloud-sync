from app.database import db_session
from app.models import IVLEFile, User, Job, IVLEAnnouncement, IVLEForumHeading, IVLEForumThread
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
                #print "---announce---"
                #print announcement["ID"]
                #print announcement["Title"]
                #print announcement["Creator"]["Name"]
                #print datetime.fromtimestamp(int(announcement["CreatedDate"][6:16]))
                #print announcement["Description"]
                db_session.add(IVLEAnnouncement(announcement, courseCode, user.user_id))
                db_session.commit()
            forums = client.get('Forums', CourseID=result['ID'], Duration=0, IncludeThreads=True, TitleOnly=False)
            print "---forum---"
            for forum in forums['Results']:
                #print forum.keys()
                #print forum["Title"]
                for heading in forum["Headings"]:
                    #print heading.keys()
                    #print heading["Title"]
                    new_heading = IVLEForumHeading(forum, heading, courseCode, user.user_id)
                    db_session.add(new_heading)
                    db_session.commit()
                    #print heading
                    exploreThreads(heading, user.user_id, new_heading.id, -1)
                    #for thread in heading["Threads"]:
                    #    print thread.keys()
                    #    print thread["ID"]
                    #    print thread["isNewPost"]
                    #    print thread["isRead"]
                    #    print thread["PostTitle"]
                    #    print thread["Poster"]["Name"]
                    #    print datetime.fromtimestamp(int(thread["PostDate"][6:16]))
                    #    print thread["PostBody"]
                    #    print thread
                    #    print thread["Threads"]
            workbins = client.get('Workbins', CourseID=result['ID'], Duration=0)
            for workbin in workbins['Results']:
                print workbin.keys()
                title = workbin['Title']
                exploreFolders(workbin, [courseCode + ' ' + title], workbin['ID'], client, user_id, courseCode)
        print "------------"


def exploreThreads(json, user_id, parent_heading_id, parent_thread_id):
    for thread in json['Threads']:
        print thread
        print "----"
        new_thread = IVLEForumThread(thread, user_id, parent_heading_id, parent_thread_id)
        db_session.add(new_thread)
        db_session.commit()
        if not len(thread['Threads']) == 0:
            exploreThreads(thread, user_id, parent_heading_id, new_thread.id)


def exploreFolders(json, parents, ivle_workbin_id, client, user_id, course_code):

    for folder in json['Folders']:
        folder_name = folder['FolderName']
        for file in folder['Files']:
            file_name = file['FileName']
            file_id = file['ID']
            file_path = '/'.join(parents + [folder_name])
            file_url = client.build_download_url(file_id)
            print file_path
            print file
            new_ivle_file = IVLEFile(file, file_path, user_id, ivle_workbin_id, course_code)
            db_session.add(new_ivle_file)
            db_session.commit()
            #db_session.add(Job(fileID, fileURL, 'http', self.user.user_id,
            #    filePath))
            #db_session.commit()
        exploreFolders(folder, parents + [folder_name], ivle_workbin_id, client, user_id, course_code)


poll_news_feed(1)