from perfrunner.helpers.local import run_custom_cmd
from perfrunner.settings import PhaseSettings, TargetSettings

CMD = " -test_duration {test_duration}" \
      " -test_total_docs {test_total_docs}" \
      " -test_query_workers {test_query_workers}" \
      " -test_kv_workers {test_kv_workers}" \
      " -test_kv_throughput_goal {test_kv_throughput_goal}" \
      " -test_data_file {test_data_file}" \
      " -test_driver {test_driver}" \
      " -test_stats_limit {test_stats_limit}" \
      " -test_stats_aggregation_step {test_stats_aggregation_step}" \
      " -test_debug {test_debug}" \
      " -test_query_type {test_query_type} " \
      " -test_query_limit {test_query_limit}" \
      " -test_query_field {test_query_field}" \
      " -test_mutation_field {test_mutation_field}" \
      " -test_worker_type {test_worker_type}" \
      " -couchbase_index_name {couchbase_index_name}" \
      " -couchbase_cluster_ip {couchbase_cluster_ip}" \
      " -couchbase_bucket {couchbase_bucket}" \
      " -couchbase_user {couchbase_user}" \
      " -couchbase_password {couchbase_password}"


def jts_run(workload_settings: PhaseSettings, target: TargetSettings,
            timer: int, worker_id: int):

    settings = workload_settings
    params = CMD.format(test_duration=settings.time,
                        test_total_docs=settings.test_total_docs,
                        test_query_workers=settings.test_query_workers,
                        test_kv_workers=settings.test_kv_workers,
                        test_kv_throughput_goal=settings.test_kv_throughput_goal,
                        test_data_file=settings.test_data_file,
                        test_driver=settings.test_driver,
                        test_stats_limit=settings.test_stats_limit,
                        test_stats_aggregation_step=settings.test_stats_aggregation_step,
                        test_debug=settings.test_debug,
                        test_query_type=settings.test_query_type,
                        test_query_limit=settings.test_query_limit,
                        test_query_field=settings.test_query_field,
                        test_mutation_field=settings.test_mutation_field,
                        test_worker_type=settings.test_worker_type,
                        couchbase_index_name=settings.couchbase_index_name,
                        couchbase_cluster_ip=target.node,
                        couchbase_bucket=target.bucket,
                        couchbase_user=target.bucket,
                        couchbase_password=target.password)

    run_custom_cmd(settings.jts_home_dir, settings.jts_run_cmd, params)


def jts_warmup(workload_settings: PhaseSettings, target: TargetSettings,
               timer: int, worker_id: int):
    settings = workload_settings
    params = CMD.format(test_duration=settings.warmup_time,
                        test_total_docs=settings.test_total_docs,
                        test_query_workers=settings.warmup_query_workers,
                        test_kv_workers="0",
                        test_kv_throughput_goal="0",
                        test_data_file=settings.test_data_file,
                        test_driver=settings.test_driver,
                        test_stats_limit=settings.test_stats_limit,
                        test_stats_aggregation_step=settings.test_stats_aggregation_step,
                        test_debug=settings.test_debug,
                        test_query_type=settings.test_query_type,
                        test_query_limit=settings.test_query_limit,
                        test_query_field=settings.test_query_field,
                        test_mutation_field=settings.test_mutation_field,
                        test_worker_type="warmup",
                        couchbase_index_name=settings.couchbase_index_name,
                        couchbase_cluster_ip=target.node,
                        couchbase_bucket=target.bucket,
                        couchbase_user=target.bucket,
                        couchbase_password=target.password)

    run_custom_cmd(settings.jts_home_dir, settings.jts_run_cmd, params)
