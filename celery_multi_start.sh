#!/bin/bash
celery multi start 4 -A ivlemods -l debug -Q:2 ivle -Q:3 dropbox -Q:4 flask
