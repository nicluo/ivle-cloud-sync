import requests

from app.database import db_session
from app.models import IVLEFile

ivle_uid = 'u0906931'
#r = requests.get('https://ivle.nus.edu.sg/jobs/sync_file.ashx?user=' + ivle_uid)
r = requests.get('http://nusmods.com/jobs/a0071932')
for file in r.json():
    db_session.add(IVLEFile(file))
    db_session.commit()