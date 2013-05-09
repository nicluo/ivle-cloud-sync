from fabric.api import cd, env, run

env.user = 'cloudsync'
env.hosts = ['ivle.nusmods.com']

def deploy():
    with cd('~/ivle-cloud-sync'):
        run('git pull')
        run('sudo pip install -r requirements.txt')
        run('/etc/init.d/celeryd restart')
        run('sudo service uwsgi restart')
