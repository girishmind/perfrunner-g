[clusters]
themis =
    172.23.96.16:kv,n1ql
    172.23.96.17:kv,n1ql
    172.23.96.20:kv,n1ql
    172.23.96.23:kv,n1ql
    172.23.97.177:eventing

[clients]
hosts =
    172.23.96.38
credentials = root:couchbase

[storage]
data = /data

[credentials]
rest = Administrator:password
ssh = root:couchbase

[parameters]
OS = CentOS 7
CPU = E5-2680 v3 (24 vCPU)
Memory = 64GB
Disk = Samsung Pro 850
