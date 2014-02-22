from fabric.api import cd, env, run

env.user = 'cloudsync'
env.hosts = ['ivle.nusmods.com']

def deploy():
    with cd('~/ivle-cloud-sync'):
        run('git pull')
        run('sudo pip install -r requirements.txt')
        run('sudo /etc/init.d/celeryd restart')
        #run('/etc/init.d/celerybeat restart')
        run('sudo service uwsgi restart')
