import sys
import json
import os
from rucio.client import Client
from rucio.client.downloadclient import DownloadClient
from rucio.client.uploadclient import UploadClient
from string import Template

class PandaTemplate(Template):
    delimiter='%'

def stage_in():
    configfile = json.load(open(sys.argv[2]))
    d = DownloadClient()
    dids = configfile['dids']
    a = d.download_dids([{'did': x, 'base_dir': os.getcwd(), 'no_subdir': True} for x in dids])

    inval = ','.join([x.split(':',1)[1] for x in dids])
    configfile = json.load(open(sys.argv[2]))
    template = configfile['exec_template']
    rendered = PandaTemplate(template).safe_substitute(IN=inval,delimiter='%')
    with open(sys.argv[3],'w') as f:
        f.write(rendered+'\n')

def stage_out():
    disk = os.environ['MINIPILOT_STAGEOUT_RSE']
    configfile = json.load(open(sys.argv[2]))
    u = UploadClient()
    outputs = configfile['outputs']
    for output in outputs:
        print('output',output)
        toupload = [{
            'path': output,
            'rse': disk,
            'did_name': 'user.{user}.{taskid}._{subjobid}.{output}'.format(
                user = configfile['user'],
                taskid = str(configfile['taskid']).zfill(8),
                subjobid = str(configfile['subjobid']).zfill(6),
                output = output
            ),
            'did_scope': 'user.{user}'.format(user = configfile['user'])
        }]
        print(json.dumps(toupload))
        u.upload(toupload)


if __name__ == '__main__':
    if sys.argv[1]=='stagein':
        stage_in()
    if sys.argv[1]=='stageout':
        stage_out()