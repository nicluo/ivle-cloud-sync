#!/bin/bash
celery multi start celery ivle dropbox flask --app=ivlemods.celery --loglevel=DEBUG -Q:ivle ivle -Q:dropbox dropbox -Q:flask flask -Q: default
