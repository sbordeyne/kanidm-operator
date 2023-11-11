# Kanidm operator

Kubernetes operator that allows you to create groups, OAuth clients, Accounts and more for kanidm


## Getting Started

First, apply the custom resource definitions to your cluster using

`kubectl apply -k https://github.com/sbordeyne/kanidm-operator/tree/master/manifests/crds`

This will apply the latest `CustomResourceDefinition` for the operator. Then, deploy the operator with

`kubectl apply -k https://github.com/sbordeyne/kanidm-operator/tree/master/manifests/operator`

Which will deploy the operator in the `kanidm-system` namespace.

To deploy kanidm using the operator, create a new `Kanidm` resource, following the examples at https://github.com/sbordeyne/kanidm-operator/tree/master/example

```yaml
apiVersion: v1alpha1
kind: Kanidm
metadata:
  name: kanidm
  namespace: kanidm
spec:
  version: 1.1.0-beta.13
  database:
    fsType: other
    storageClass: nfs-client
    storageSize: 1Gi
  domain: idm.example.com
  certificate:
    issuer: cluster-issuer
  logLevel: info
  backup:
    enabled: true
    schedule: "0 9 * * *"
    versions: 7
    storageClass: nfs-client
    storageSize: 7Gi
  webPort: 8443
  ldapPort: 3890
  highAvailability:
    enabled: false
    replicas: 1
```

If the operator is running, and kanidm is deployed, you can then use the operator to create groups, accounts, service accounts, OAuth2 clients and more using the provided CRDs. Note that if you deployed kanidm without the operator, it will not be able to access the server (you could trick it by renaming your service `kanidm-svc` and adding both the `admin` and `idm-admin` secrets in the `kanidm-system` namespace)


```
(?<anchor>now|\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}:\d{2}(,\d{3})?)?\|\|)(?<sign>[-+])(?<amount>\d+?)(?<unit>[smhdDWMyY])(\/(?<rounding>[smhdwMy]))?
```
