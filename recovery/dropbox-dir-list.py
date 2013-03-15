import os

from ivlemods.models import User, Job, OnlineStore, IVLEFile
from ivlemods import app
from dropbox import client, rest, session

class SessionHandler():
    def __init__(self, user_id):
        user = User.query.get(user_id)
        print "Session - logging in as user", user.user_id
        if user.dropbox_key == None or user.dropbox_secret == None:
            raise Exception("DROPBOX_USR_ERR")

        sess = session.DropboxSession(app.config['DROPBOX_APP_KEY'],
            app.config['DROPBOX_APP_SECRET'], app.config['DROPBOX_ACCESS_TYPE'])
        sess.set_token(user.dropbox_key, user.dropbox_secret)
        self.client = client.DropboxClient(sess)

def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

user = raw_input("login as ?n:")

if not is_number(user):
    print "user is not a number."
    quit()

SH = SessionHandler(int(user))

path = ""
path_stack = []
while(1):
    root = SH.client.metadata(path)
    contents = {}
    print "current directory:", path + "/"
    print 0, "/.."
    index = 1
    for content in root["contents"]:
        contents[index] = content["path"]
        if content["is_dir"]:
            print index, os.path.basename(content["path"]) + "/", content["revision"]
        else:
            print index, os.path.basename(content["path"]), content["revision"]
        index += 1

    input = raw_input("command ?n/q/rm ?n:")

    split_input = input.split(" ")
    #print split_input
    if(input == 'q'):
        exit()
    elif len(split_input) > 0 and split_input[0] == 'rm':
        if is_number(split_input[1]):
            print "removing", contents[int(split_input[1])]
            result = SH.client.file_delete(contents[int(split_input[1])])
            print "success"
        else:
            print "rm: invalid args"
        continue

    if is_number(input) and int(input) > 0:
        path_stack.append(path)
        path = contents[int(input)]
    elif is_number(input) and int(input) == 0:
        if not len(path_stack):
            path_stack.append("")
        path = path_stack.pop()



