# k8s-datasetjob-crd
HEP style dataset job CRD

## Requirements
* `docker`
* `kind`
* `kubectl`

## Create a Kubernetes Cluster 
```
kind create cluster
export KUBECONFIG="$(kind get kubeconfig-path --name="1")"
```

## Create CRD and Controller

- make sure to create a file `grid` with the grid password and point it to your key/cert pair
- in `hook.yml` and `slicejob_template.json` the rucio username `lheinric` is user but would
  normally be a pilot/robot account

```
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/metacontroller/master/manifests/metacontroller-rbac.yaml
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/metacontroller/master/manifests/metacontroller.yaml
kubectl create configmap dsjobset-controller --from-file=sync.py --from-file=slicejob_template.json
kubectl create configmap minipilot --from-file=minipilot.py
kubectl create -f crd.yml -f hook.yml -f ctrl.yml
kubectl create secret generic gridpw --from-file=grid --from-file=$HOME/.globus/userkey.pem --from-file=$HOME/.globus/usercert.pem
```

## Create Dataset Job 

Change `taskid` (some number) and `outDS` (some name)
- must be unique, as overwrite will fail
- taskid controls naming of subjob outputs

```
kubectl create -f dsjob.yml
```
