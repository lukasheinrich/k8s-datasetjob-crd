from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
from rucio.client import Client
import logging
logging.basicConfig(level = logging.WARNING)
log = logging.getLogger(__name__)

def generate_desired(gridjobspec):
    c = Client()
    scope,name = gridjobspec['inDS'].split(':',1)
    nFilesPerJob = gridjobspec.get('nFilesPerJob',3)
    files = sorted(list(c.list_files(scope,name))   )

    def chunks(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]
    filelists = list(chunks(files,nFilesPerJob))

    jobtemplate = json.load(open('slicejob_template.json'))

    configmaps = []
    jobs = []
    for index,fl in enumerate(filelists):
        cmapname = 'task-{taskid}-{index}-config'.format(taskid = gridjobspec['taskid'], index = index)
        jobname = 'task-{taskid}-{index}-job'.format(taskid = gridjobspec['taskid'], index = index)
        namespace = 'default'
        jobconfig = {
            "dids": sorted([':'.join([x['scope'],x['name']]) for x in fl]),
            "exec_template": gridjobspec['exec_template'],
            "outputs": gridjobspec['outputs'],
            "taskid": gridjobspec['taskid'],
            "subjobid": index,
            "user": gridjobspec['user']
        }
        configmap = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': cmapname,
                'namespace': namespace
            },
            'data': {
                'jobconfig.json': json.dumps(jobconfig, sort_keys = True)
            }
        }

        job = json.load(open('slicejob_template.json'))
        job['metadata']['name'] = jobname
        job['metadata']['namespace'] = namespace
        job['spec']['template']['spec']['volumes'][0]['configMap']['name'] = cmapname
        job['spec']['template']['spec']['initContainers'][1]['image'] = gridjobspec['image']
        configmaps.append(configmap)
        jobs.append(job)

    children = configmaps + jobs
    import hashlib
    log.warning('children hash %s',hashlib.sha1(json.dumps(children, sort_keys = True)).hexdigest())
    return len(jobs),children

def observed_counts(observed_jobs, total):
   succeeded = 0
   failed = 0
   active = 0
   for j,js in observed_jobs.items():
      log.warning(js['status'])
      succeeded += js['status'].get('succeeded',0)
      active += js['status'].get('active',0)
      failed += js['status'].get('failed',0)
   log.warning('counts %s %s %s',succeeded,failed,active)
   return {'succeeded': succeeded, 'failed': failed,'active': active}

def make_outDS(spec):
    c = Client()
    scope = 'user.{}'.format(spec['user'])
    outputs = spec['outputs']
    taskid = spec['taskid']
    outDS_stub = spec['outDS']
    for out in outputs:
        files = [
            {'name':x, 'scope': scope}
            for x in c.list_dids(scope,{
                'name':'user.{user}.{taskid}.*.{output}'.format(
                    user = spec['user'],
                    taskid =  str(taskid).zfill(8),
                    output = out
                    )
                },type='file')
        ]
        ds_name = '{}_{}'.format(outDS_stub.split(':',1)[-1],out)
        log.warning('creating outDS {}:{}'.format(scope,ds_name))
        c.add_dataset(scope,ds_name, files = files)

class Controller(BaseHTTPRequestHandler):
   def sync(self, parent, children):
      log.warning('syncing! %s',parent)
      spec  = parent.get("spec", {})
      # Compute status based on observed state.

      last_total = parent.get('status',{}).get('total')
      last_counts = observed_counts(children["Job.batch/v1"], last_total)
      last_outds = parent.get('status',{}).get('outds',False)
      if last_counts['succeeded'] == last_total and not last_outds:
         log.warning('all done!')
         make_outDS(spec)
         last_outds = True
         log.warning('made outDS!')


      njobs, desired_children = generate_desired(spec)

      computed_status = {
         "jobs": len(children["Job.batch/v1"]),
         "subjobs": last_counts,
         "outds": last_outds,
         "total": njobs
      }

      return {"status": computed_status, "children": desired_children}

   def do_POST(self):
      # Serve the sync() function as a JSON webhook.
      observed = json.loads(self.rfile.read(int(self.headers.getheader("content-length"))))
      desired = self.sync(observed["parent"], observed["children"])


      log.warning('write status %s',desired['status'])

      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps(desired, sort_keys = True))

HTTPServer(("", 80), Controller).serve_forever()
