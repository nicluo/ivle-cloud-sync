#!/usr/bin/env python
from datetime import datetime

from ivlemods.database import db_session
from ivlemods.ivle import IvleClient
from ivlemods.models import User

for user in User.query.all():
    client = IvleClient(user.ivle_token)
    validation = client.get('Validate')
    if validation['Success']:
        user.ivle_valid_till = datetime.fromtimestamp(int(validation['ValidTill'][6:16]))
        if validation['Token'] != user.ivle_token:
            user.ivle_token = validation['Token']
        db_session.commit()
