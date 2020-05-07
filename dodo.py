import os
import json

from doit.tools import LongRunning
from subprocess import check_output, CalledProcessError, PIPE

DIR = os.path.abspath(os.path.dirname(__file__))
CWD = os.path.abspath(os.getcwd())
REL = os.path.relpath(DIR, CWD)

DOIT_CONFIG = {
    'default_tasks': ['test'],
    'verbosity': 2,
}

def call(cmd, stderr=PIPE, shell=True, **kwargs):
    result = check_output(
        cmd,
        stderr=stderr,
        shell=shell,
        **kwargs).decode('utf-8').rstrip()
    return result

def aws_account():
    cmd = 'aws sts get-caller-identity'
    try:
        result = call(cmd)
        obj = json.loads(result)
        return obj['Account']
    except CalledProcessError as cpe:
        if 'Unable to locate credentials' in cpe.stderr.decode():
            return 'MISSING_CREDENTIALS'

def reponame():
    cmd = 'basename $(git rev-parse --show-toplevel)'
    result = call(cmd, cwd=DIR)
    return result

AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
AWS_ACCOUNT = os.getenv('AWS_ACCOUNT', aws_account())
REPONAME = os.getenv('REPONAME', reponame())
REPOURL = f'{AWS_ACCOUNT}.dkr.ecr.{AWS_REGION}.amazonaws.com/{REPONAME}'
NGINX_INFLUXDB_VERSION = call('git describe --match "v*" --abbrev=7')

def envs(sep=' ', **kwargs):
    envs = dict(
        AWS_REGION=AWS_REGION,
        AWS_ACCOUNT=AWS_ACCOUNT,
    )
    return sep.join(
        [f'{key}={value}' for key, value in sorted(dict(envs, **kwargs).items())]
    )

def task_build():
    cmds = [
        f'env {envs()} docker build . -t {REPOURL}:{NGINX_INFLUXDB_VERSION}',
        f'env {envs()} docker image prune -f --filter label=stage=intermediate',
    ]
    return {
        'actions': cmds,
    }

def task_login():
    cmd = f'aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {REPOURL}'
    return {
        'actions': [
            cmd,
        ],
    }

def task_publish():
    cmd = f'docker push {REPOURL}:{NGINX_INFLUXDB_VERSION}'
    return {
        'task_dep': [
            'login',
        ],
        'actions': [
            cmd,
        ],
    }
