from app.database import db_session
from app.models import IVLEFile, User, Job, IVLEAnnouncement, IVLEForumHeading, IVLEForumThread
from app.ivle import IvleClient
from datetime import datetime
from time import time

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


def get_announcements(user_id, duration=0):
    db_announcements = IVLEAnnouncement.query.filter(IVLEAnnouncement.user_id == user_id)\
        .filter(IVLEAnnouncement.is_deleted == False)\
        .all()
    poll = False
    for announcement in db_announcements:
        time_diff = datetime.now() - announcement.checked
        if time_diff.total_seconds() > duration*60:
            poll = True
    if poll or len(db_announcements) == 0:
        poll_news_feed(user_id)
        db_announcements = IVLEAnnouncement.query.filter(IVLEAnnouncement.user_id == user_id)\
            .filter(IVLEAnnouncement.is_deleted == False)\
            .all()
    announcements = []
    for announcement in db_announcements:
        announcements.append({"type" : "announcement",
                             "ivle_id" : announcement.ivle_id,
                             "course_code" : announcement.course_code,
                             "created_date" : announcement.created_date,
                             "creator" : announcement.announcement_creator,
                             "title" : announcement.announcement_title,
                             "body" : announcement.announcement_body,
                             "is_read" : announcement.is_read})
    return announcements


def get_forum_headings(user_id, duration=0):
    pass


def get_forum_threads(user_id, duration=0):
    pass


def get_files(user_id, duration=0):
    pass


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
                try:
                    db_announcement = IVLEAnnouncement.query\
                                         .filter(IVLEAnnouncement.user_id == user.user_id)\
                                         .filter(IVLEAnnouncement.ivle_id == announcement['ID'])\
                                         .one()
                    db_announcement.checked = datetime.now()
                    db_session.commit()
                except MultipleResultsFound as e:
                    pass
                except NoResultFound as e:
                    db_session.add(IVLEAnnouncement(announcement, courseCode, user.user_id))
                    db_session.commit()
            forums = client.get('Forums', CourseID=result['ID'], Duration=0, IncludeThreads=True, TitleOnly=False)
            #print "---forum---"
            for forum in forums['Results']:
                #print forum.keys()
                #print forum["Title"]
                for heading in forum["Headings"]:
                    #print heading.keys()
                    #print heading["Title"]
                    try:
                        heading_db_entry = IVLEForumHeading.query\
                            .filter(IVLEForumHeading.user_id == user.user_id)\
                            .filter(IVLEForumHeading.ivle_heading_id == heading['ID'])\
                            .one()
                    except MultipleResultsFound as e:
                        pass
                    except NoResultFound as e:
                        heading_db_entry = IVLEForumHeading(forum, heading, courseCode, user.user_id)
                        db_session.add(heading_db_entry)
                        db_session.commit()

                    #print heading
                    exploreThreads(heading, user.user_id, heading_db_entry.id, -1)
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
                #print workbin.keys()
                title = workbin['Title']
                exploreFolders(workbin, [courseCode + ' ' + title], workbin['ID'], client, user_id, courseCode)
        #print "------------"


def exploreThreads(json, user_id, parent_heading_id, parent_thread_id):
    for thread in json['Threads']:
        #print thread
        #print "----"
        try:
            thread_db_entry = IVLEForumThread.query\
                                .filter(IVLEForumThread.user_id == user_id)\
                                .filter(IVLEForumThread.ivle_id == thread['ID'])\
                                .one()
        except MultipleResultsFound as e:
            pass
        except NoResultFound as e:
            thread_db_entry = IVLEForumThread(thread, user_id, parent_heading_id, parent_thread_id)
            db_session.add(thread_db_entry)
            db_session.commit()

        if thread['Threads']:
            exploreThreads(thread, user_id, parent_heading_id, thread_db_entry.id)


def exploreFolders(json, parents, ivle_workbin_id, client, user_id, course_code):

    for folder in json['Folders']:
        folder_name = folder['FolderName']
        for file in folder['Files']:
            file_id = file['ID']
            file_path = '/'.join(parents + [folder_name])
            file_url = client.build_download_url(file_id)
            #print file_path
            #print file
            try:
                IVLEFile.query\
                    .filter(IVLEFile.user_id == user_id)\
                    .filter(IVLEFile.ivle_file_id == file_id)\
                    .one()
            except MultipleResultsFound as e:
                pass
            except NoResultFound as e:
                new_ivle_file = IVLEFile(file, file_path, user_id, ivle_workbin_id, course_code)
                db_session.add(new_ivle_file)
                db_session.commit()
                #db_session.add(Job(fileID, fileURL, 'http', self.user.user_id, filePath))
                #db_session.commit()
        exploreFolders(folder, parents + [folder_name], ivle_workbin_id, client, user_id, course_code)


poll_news_feed(1)
print get_announcements(1)