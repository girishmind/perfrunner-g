from argparse import ArgumentParser

import yaml
from jinja2 import Environment, FileSystemLoader, Template

from logger import logger
from perfrunner.utils.cloudrunner import CloudRunner

MEMORY_QUOTAS = {
    'c4.4xlarge':  24576,   # 30GB RAM
    'c4.8xlarge':  54272,   # 60GB RAM

    'c5.4xlarge':  26624,   # 32GB RAM
    'c5.9xlarge':  61440,   # 72GB RAM

    'm4.2xlarge':  26624,   # 32GB RAM
    'm4.4xlarge':  56320,   # 64GB RAM
    'm4.10xlarge': 143360,  # 160GB RAM
    'm4.16xlarge': 225280,  # 256GB RAM

    'r4.2xlarge':  54272,   # 61GB RAM
    'r4.4xlarge':  102400,  # 122GB RAM
    'r4.8xlarge':  209920,  # 244GB RAM

    'i3.8xlarge':  [209920, '32vCPU', '4 x 1900 NVMe SSD', 'RHEL 7.3'],   # 244GB RAM
    'i3.4xlarge':  [102400, '16vCPU', '2 x 1.9 NVMe SSD', 'RHEL 7.3']     # 122 GB RAM
}

OUTPUT_FILE = 'custom'

TEMPLATES_DIR = 'templates'

TEMPLATES = (
    'full_cluster.spec',
    'kv_cluster.spec',
    'pillowfight.test',
    'ycsb_workload_a.test',
    'ycsb_workload_d.test',
    'ycsb_workload_e.test',
    'ycsb_workloada_latency.test',
    'ycsb_workloade_latency.test'
)

THREADS_PER_CLIENT = {
    'pillowfight.test': 20,
    'ycsb_workload_a.test': 20,
    'ycsb_workload_d.test': 20,
    'ycsb_workload_e.test': 20,
    'ycsb_workloada_latency.test': 20,
    'ycsb_workloade_latency.test': 20
}


def get_templates(template: str) -> Template:
    loader = FileSystemLoader(searchpath=TEMPLATES_DIR)
    env = Environment(loader=loader, keep_trailing_newline=True)
    return env.get_template(template)


def render_test(template: str, instance: str, threads: int, server_instances: int):
    mem_quota = MEMORY_QUOTAS[instance][0]
    workload_instances = estimate_num_clients(template, threads)
    num_replica = server_instances-1
    content = render_template(get_templates(template),
                              mem_quota=mem_quota,
                              workers=THREADS_PER_CLIENT[template],
                              workload_instances=workload_instances,
                              server_instances=server_instances,
                              instance=instance,
                              num_replica=num_replica)
    filename = template.split('.')[0] + '_' + str(server_instances) + 'nodes'
    store_cfg(content, extension='.test', filename=filename)


def render_spec(template: str, instance: str):
    with open(CloudRunner.EC2_META) as fp:
        meta = yaml.load(fp)
        clients = meta.get('clients', {}).values()
        servers = meta.get('servers', {}).values()
    mem_quota = MEMORY_QUOTAS[instance][0]/1024
    cpu_info = MEMORY_QUOTAS[instance][1]
    storage_info = MEMORY_QUOTAS[instance][2]
    os_info = MEMORY_QUOTAS[instance][3]

    content = render_template(get_templates(template),
                              servers=servers,
                              clients=clients,
                              mem_quota=mem_quota,
                              cpu_info=cpu_info,
                              storage_info=storage_info,
                              os_info=os_info)
    filename = 'aws_' + instance
    store_cfg(content, extension='.spec', filename=filename)


def render_inventory(instance: str):
    with open(CloudRunner.EC2_META) as fp:
        meta = yaml.load(fp)
        servers = meta.get('servers', {}).values()

    content = render_template(get_templates('inventory.ini'),
                              servers=servers)
    store_cfg(content, '.ini', filename=instance)


def estimate_num_clients(template: str, threads: int) -> int:
    return max(1, threads // THREADS_PER_CLIENT[template])


def render_template(t: Template, **kwargs) -> str:
    return t.render(**kwargs)


def store_cfg(content: str, extension: str, filename: str):
    filename = '{}'.format(filename).replace('.', '_')
    logger.info('Creating a new file: {}{}'.format(filename, extension))
    with open('{}{}'.format(filename, extension), 'w') as f:
        f.write(content)


def main():
    parser = ArgumentParser()

    parser.add_argument('--instance', dest='instance', type=str,
                        choices=list(MEMORY_QUOTAS))
    parser.add_argument('--template', dest='template', type=str,
                        choices=TEMPLATES,
                        required=True)
    parser.add_argument('--threads', dest='threads', type=int,
                        default=1,
                        help='Total number of workload generator threads')
    parser.add_argument('--num-servers', dest='server_instances', type=int,
                        default=0,
                        help='Total number of nodes')

    args = parser.parse_args()

    if '.test' in args.template:
        render_test(args.template, args.instance, args.threads, args.server_instances)
    else:
        render_spec(args.template, args.instance)
        render_inventory(args.instance)


if __name__ == '__main__':
    main()
