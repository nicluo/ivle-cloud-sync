from ivlemods.database import db_session
from ivlemods.models import IVLEFile, User, Job, IVLEAnnouncement, IVLEForumHeading, IVLEForumThread
from ivlemods.ivle import IvleClient
from datetime import datetime
import logging
from re import escape

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

logger = logging.getLogger(__name__)


def get_announcements(user_id, duration=0):
    logger.info("GET - Announcements for user %s.", user_id)
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
    logger.info("GET - Forum headings for user %s.", user_id)
    db_forum_headings = IVLEForumHeading.query.filter(IVLEForumHeading.user_id == user_id)\
        .filter(IVLEForumHeading.is_deleted == False)\
        .all()
    poll = False
    for forum_heading in db_forum_headings:
        time_diff = datetime.now() - forum_heading.checked
        if time_diff.total_seconds() > duration*60:
            poll = True
    if poll or len(db_forum_headings) == 0:
        poll_news_feed(user_id)
        db_forum_headings = IVLEForumHeading.query.filter(IVLEForumHeading.user_id == user_id)\
            .filter(IVLEForumHeading.is_deleted == False)\
            .all()
    json = []
    for elem in db_forum_headings:
        json.append({"type": "forum_heading",
                     "ivle_id": elem.ivle_heading_id,
                     "ivle_forum_id": elem.ivle_forum_id,
                     "course_code": elem.course_code,
                     "created_date": elem.modified_timestamp,
                     "forum_title": elem.forum_title,
                     "heading_title": elem.heading_title})
    return json


def get_forum_threads(user_id, duration=0):
    logger.info("GET - Forum threads for user %s.", user_id)
    db_forum_threads = IVLEForumThread.query.filter(IVLEForumThread.user_id == user_id)\
        .filter(IVLEForumThread.is_deleted == False)\
        .all()
    poll = False
    for elem in db_forum_threads:
        time_diff = datetime.now() - elem.checked
        if time_diff.total_seconds() > duration * 60:
            poll = True
    if poll or len(db_forum_threads) == 0:
        poll_news_feed(user_id)
        db_forum_threads = IVLEForumThread.query.filter(IVLEForumThread.user_id == user_id)\
            .filter(IVLEForumThread.is_deleted == False)\
            .all()
    json = []
    for elem in db_forum_threads:
        json.append({"type": "forum_thread",
                     "ivle_id": elem.ivle_id,
                     "parent_thread_id": elem.parent_thread_id,
                     "parent_heading_id": elem.parent_heading_id,
                     "course_code": elem.course_code,
                     "post_creator": elem.post_creator,
                     "post_title": elem.post_title,
                     "post_body": elem.post_body,
                     "created_date": elem.created_date
                     })
    return json


def get_files(user_id, duration=0):
    logger.info("GET - Files for user %s.", user_id)
    db_files = IVLEFile.query.filter(IVLEFile.user_id == user_id)\
        .filter(IVLEFile.is_deleted == False)\
        .all()
    poll = False
    for elem in db_files:
        time_diff = datetime.now() - elem.checked
        if time_diff.total_seconds() > duration * 60:
            poll = True
    if poll or len(db_files) == 0:
        poll_news_feed(user_id)
        db_files = IVLEFile.query.filter(IVLEFile.user_id == user_id)\
            .filter(IVLEFile.is_deleted == False)\
            .all()
    json = []
    for elem in db_files:
        json.append({"type": "file",
                     "ivle_id": elem.ivle_file_id,
                     "workbin_id": elem.ivle_workbin_id,
                     "course_code": elem.course_code,
                     "file_path": elem.file_path,
                     "file_name": elem.file_name
        })
    return json


def poll_news_feed(user_id):
    logger.info("POLL - IVLE news feed for user %s.", user_id)
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
                        heading_db_entry.checked = datetime.now()
                        db_session.commit()
                    except MultipleResultsFound as e:
                        pass
                    except NoResultFound as e:
                        heading_db_entry = IVLEForumHeading(forum, heading, courseCode, user.user_id)
                        db_session.add(heading_db_entry)
                        db_session.commit()

                    #print heading
                    exploreThreads(heading, user.user_id, heading_db_entry.id, -1, courseCode)
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
                exploreFolders(workbin, [escape(courseCode) + ' ' + escape(title)], workbin['ID'], client, user_id, courseCode)
        #print "------------"


def exploreThreads(json, user_id, parent_heading_id, parent_thread_id, course_code):
    for thread in json['Threads']:
        #print thread
        #print "----"
        try:
            thread_db_entry = IVLEForumThread.query\
                                .filter(IVLEForumThread.user_id == user_id)\
                                .filter(IVLEForumThread.ivle_id == thread['ID'])\
                                .one()
            thread_db_entry.checked = datetime.now()
            db_session.commit()
        except MultipleResultsFound as e:
            pass
        except NoResultFound as e:
            thread_db_entry = IVLEForumThread(thread, user_id, parent_heading_id, parent_thread_id, course_code)
            db_session.add(thread_db_entry)
            db_session.commit()

        if thread['Threads']:
            exploreThreads(thread, user_id, parent_heading_id, thread_db_entry.id, course_code)


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
                db_file = IVLEFile.query\
                        .filter(IVLEFile.user_id == user_id)\
                        .filter(IVLEFile.ivle_file_id == file_id)\
                        .one()
                db_file.checked = datetime.now()
                db_session.commit()
            except MultipleResultsFound as e:
                pass
            except NoResultFound as e:
                new_ivle_file = IVLEFile({'user_id': user_id,\
                                          'course_code': course_code,\
                                          'ivle_workbin_id': ivle_workbin_id,\
                                          'ivle_file_id': file['ID'],\
                                          'ivle_folder_id': folder['ID'],\
                                          'file_path': file_path,\
                                          'file_name': file['FileName']})
                db_session.add(new_ivle_file)
                db_session.commit()
                #db_session.add(Job(fileID, fileURL, 'http', self.user.user_id, filePath))
                #db_session.commit()
        exploreFolders(folder, parents + [folder_name], ivle_workbin_id, client, user_id, course_code)


print get_announcements(1, 2)
print get_forum_headings(1, 2)
print get_forum_threads(1, 2)
print get_files(1, 0)