[clusters]
leto =
    leto-srv-01.perf.couchbase.com:kv
    leto-srv-02.perf.couchbase.com:kv
    leto-srv-03.perf.couchbase.com:kv
    leto-srv-04.perf.couchbase.com:kv

[clients]
hosts =
    leto-cnt-01.perf.couchbase.com
credentials = root:couchbase

[storage]
data = /data
index = /index
backup = /workspace/backup

[credentials]
rest = Administrator:password
ssh = root:couchbase

[parameters]
OS = CentOS 7
CPU = E5-2630 (24 vCPU)
Memory = 64 GB
Disk = Samsung Pro 850
