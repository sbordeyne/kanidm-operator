"""
Controls the deployment of kanidm in the cluster.
Will read the kanidms.kanidm.github.io CRD to deploy either:
  - In High Availability mode : n read replicas of kanidm, 1 write replica with UI
  - In Single Instance mode : 1 kanidm instance with UI as a deployment
"""
