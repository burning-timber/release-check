import json
import boto3
import os
from urllib import request
from urllib.error import HTTPError

ecr = boto3.client('ecr')
codebuild = boto3.client('codebuild')

password_mgr = request.HTTPPasswordMgrWithDefaultRealm()
password_mgr.add_password(None, "https://api.github.com", os.environ.get('GITHUB_API_USER'), os.environ.get('GITHUB_API_PASS'))
handler = request.HTTPBasicAuthHandler(password_mgr)
opener = request.build_opener(handler)
request.install_opener(opener)

def lambda_handler(event, context):
    projects = os.environ.get('CODEBUILD_PROJECTS').split(',')
    projects = codebuild.batch_get_projects(names=projects)['projects']
    for project in projects:
        for tag in project['tags']:
            if tag['key'] == "ecr_repo":
                ecr_repo = tag['value']

        if project['source']['type'] == 'GITHUB':
            repo_api = project['source']['location'] \
                .replace("https://github.com", "https://api.github.com/repos")
            latest_tag = json.loads(request.urlopen('{}/releases/latest'.format(repo_api)).read())['tag_name']
            tag_ids = [ image['imageTag'] for image in ecr.list_images(repositoryName=ecr_repo)['imageIds'] ]
            if latest_tag not in tag_ids:
                print("New release {} for {} found. Starting docker build.".format(latest_tag, project['name']))
                codebuild.start_build(projectName=project['name'], sourceVersion=latest_tag)
            else:
                print("Project {} up to date.  Skipping".format(project['name']))
