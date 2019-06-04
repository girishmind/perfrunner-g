import os

from perfrunner.helpers import local
from perfrunner.helpers.cbmonitor import timeit, with_stats
from perfrunner.settings import LoadSettings, TargetIterator
from perfrunner.tests import PerfTest


class BackupRestoreTest(PerfTest):

    def extract_tools(self):
        local.extract_cb(filename='couchbase.rpm')

    def flush_buckets(self):
        for i in range(self.test_config.cluster.num_buckets):
            bucket = 'bucket-{}'.format(i + 1)
            self.rest.flush_bucket(self.master_node, bucket)

    def backup(self, mode=None):
        local.backup(
            master_node=self.master_node,
            cluster_spec=self.cluster_spec,
            threads=self.test_config.backup_settings.threads,
            wrapper=self.rest.is_community(self.master_node),
            mode=mode,
            compression=self.test_config.backup_settings.compression,
            storage_type=self.test_config.backup_settings.storage_type,
            sink_type=self.test_config.backup_settings.sink_type,
            shards=self.test_config.backup_settings.shards
        )

    def compact(self):
        snapshots = local.get_backup_snapshots(self.cluster_spec)
        local.compact(self.cluster_spec,
                      snapshots,
                      self.rest.is_community(self.master_node)
                      )

    def restore(self):
        local.drop_caches()

        local.restore(cluster_spec=self.cluster_spec,
                      master_node=self.master_node,
                      threads=self.test_config.restore_settings.threads,
                      wrapper=self.rest.is_community(self.master_node))

    def backup_list(self):
        snapshots = local.get_backup_snapshots(self.cluster_spec)
        local.cbbackupmgr_list(cluster_spec=self.cluster_spec,
                               snapshots=snapshots)

    def run(self):
        self.extract_tools()

        self.load()
        self.wait_for_persistence()


class BackupTest(BackupRestoreTest):

    @with_stats
    @timeit
    def backup(self, mode=None):
        super().backup(mode)

    def _report_kpi(self, time_elapsed):
        edition = self.rest.is_community(self.master_node) and 'CE' or 'EE'
        backup_size = local.calc_backup_size(self.cluster_spec)

        backing_store = self.test_config.backup_settings.storage_type
        sink_type = self.test_config.backup_settings.sink_type

        tool = 'backup'
        if backing_store:
            tool += '-' + backing_store
        elif sink_type:
            tool += '-' + sink_type

        self.reporter.post(
            *self.metrics.bnr_throughput(time_elapsed,
                                         edition,
                                         tool=tool)
        )

        if sink_type != 'blackhole':
            self.reporter.post(
                *self.metrics.backup_size(
                    backup_size,
                    edition,
                    tool=tool if backing_store or sink_type else None)
            )

    def run(self):
        super().run()

        time_elapsed = self.backup()

        self.report_kpi(time_elapsed)


class BackupSizeTest(BackupTest):

    def _report_kpi(self, *args):
        edition = self.rest.is_community(self.master_node) and 'CE' or 'EE'
        backup_size = local.calc_backup_size(self.cluster_spec)

        self.reporter.post(
            *self.metrics.backup_size(backup_size, edition)
        )


class BackupTestWithCompact(BackupRestoreTest):

    @with_stats
    @timeit
    def compact(self):
        super().compact()

    def _report_kpi(self, time_elapsed: float, backup_size_difference: float):
        edition = self.rest.is_community(self.master_node) and 'CE' or 'EE'
        backing_store = self.test_config.backup_settings.storage_type

        tool = 'compact'
        if backing_store:
            tool += '-' + backing_store

        self.reporter.post(
            *self.metrics.compact_size_diff(
                backup_size_difference,
                edition,
                tool)
        )

        self.reporter.post(
            *self.metrics.tool_time(
                time_elapsed,
                edition,
                tool)
        )

    def run(self):
        super().run()

        self.backup()
        self.wait_for_persistence()

        initial_size = local.calc_backup_size(self.cluster_spec)
        compact_time = self.compact()
        compacted_size = local.calc_backup_size(self.cluster_spec)
        size_diff = initial_size - compacted_size

        self.report_kpi(compact_time, size_diff)


class BackupUnderLoadTest(BackupTest):

    def run(self):
        super(BackupTest, self).run()

        self.hot_load()

        self.access_bg()

        time_elapsed = self.backup()

        self.report_kpi(time_elapsed)


class BackupIncrementalTest(BackupRestoreTest):

    @timeit
    @with_stats
    def backup_with_stats(self, mode=False):
        super().backup(mode=mode)

    def _report_kpi(self, time_elapsed: int, backup_size: float):
        edition = self.rest.is_community(self.master_node) and 'CE' or 'EE'
        backing_store = self.test_config.backup_settings.storage_type
        sink_type = self.test_config.backup_settings.sink_type

        tool = 'backup-incremental'
        if backing_store:
            tool += '-' + backing_store
        elif sink_type:
            tool += '-' + sink_type

        self.reporter.post(
            *self.metrics.tool_time(time_elapsed,
                                    edition,
                                    tool=tool)
        )

        if sink_type != 'blackhole':
            self.reporter.post(
                *self.metrics.backup_size(
                    backup_size,
                    edition,
                    tool=tool)
            )

    def run(self):
        self.extract_tools()

        self.load()
        self.wait_for_persistence()
        self.backup()

        initial_backup_size = local.calc_backup_size(self.cluster_spec,
                                                     rounded=False)

        self.access()
        self.wait_for_persistence()

        # Define a secondary load. For this we borrow the 'creates' field,
        # since load doesn't normally use this anyway.
        inc_load = self.test_config.load_settings.creates
        workers = self.test_config.load_settings.workers
        size = self.test_config.load_settings.size

        # New key prefix needed to create incremental dataset.
        self.load(settings=LoadSettings({"items": inc_load,
                                         "workers": workers,
                                         "size": size}),
                  target_iterator=TargetIterator(self.cluster_spec,
                                                 self.test_config,
                                                 prefix='inc-'))
        self.wait_for_persistence()

        inc_backup_time = self.backup_with_stats(mode=True)
        total_backup_size = local.calc_backup_size(self.cluster_spec,
                                                   rounded=False)
        inc_backup_size = round(total_backup_size - initial_backup_size, 2)

        self._report_kpi(inc_backup_time, inc_backup_size)


class MergeTest(BackupRestoreTest):

    @timeit
    @with_stats
    def merge(self):
        snapshots = local.get_backup_snapshots(self.cluster_spec)

        local.drop_caches()

        # Pre build 6.5.0-3198 there was no threads flag in merge. To ensure
        # tests run across versions, omit this flag pre this build.
        version, build_number = self.build.split('-')
        build = tuple(map(int, version.split('.'))) + (int(build_number),)

        if build < (6, 5, 0, 3198):
            threads = None
        else:
            threads = self.test_config.backup_settings.threads

        local.cbbackupmgr_merge(self.cluster_spec,
                                snapshots,
                                self.test_config.backup_settings.storage_type,
                                threads)

    def _report_kpi(self, time_elapsed):
        edition = self.rest.is_community(self.master_node) and 'CE' or 'EE'
        tool = 'merge'
        if self.test_config.backup_settings.storage_type:
            tool += '-' + self.test_config.backup_settings.storage_type

        self.reporter.post(
            *self.metrics.merge_throughput(time_elapsed, edition, tool)
        )

    def run(self):
        self.extract_tools()

        self.load()
        self.wait_for_persistence()
        self.backup()  # 1st snapshot

        self.load()
        self.wait_for_persistence()
        self.backup(mode=True)  # 2nd snapshot

        time_elapsed = self.merge()

        self.report_kpi(time_elapsed)


class RestoreTest(BackupRestoreTest):

    @with_stats
    @timeit
    def restore(self):
        super().restore()

    def _report_kpi(self, time_elapsed):
        edition = self.rest.is_community(self.master_node) and 'CE' or 'EE'

        backing_store = self.test_config.backup_settings.storage_type
        sink_type = self.test_config.backup_settings.sink_type

        tool = 'restore'
        if backing_store:
            tool += '-' + backing_store
        elif sink_type:
            tool += '-' + sink_type

        self.reporter.post(
            *self.metrics.bnr_throughput(time_elapsed,
                                         edition,
                                         tool=tool)
        )

    def run(self):
        super().run()

        self.backup()

        self.flush_buckets()

        time_elapsed = self.restore()

        self.report_kpi(time_elapsed)


class ListTest(BackupRestoreTest):

    def _report_kpi(self, time_elapsed: float):

        edition = self.rest.is_community(self.master_node) and 'CE' or 'EE'
        backing_store = self.test_config.backup_settings.storage_type

        tool = 'list'
        if backing_store:
            tool += '-' + backing_store

        self.reporter.post(
            *self.metrics.tool_time(time_elapsed,
                                    edition,
                                    tool=tool))

    @with_stats
    @timeit
    def backup_list(self):
        super().backup_list()

    def run(self):
        super().run()

        self.backup()
        local.drop_caches()
        list_time = self.backup_list()
        self.report_kpi(list_time)


class ExportImportTest(BackupRestoreTest):

    def export(self):

        export_settings = self.test_config.export_settings

        local.cbexport(master_node=self.master_node,
                       cluster_spec=self.cluster_spec,
                       bucket=self.test_config.buckets[0],
                       data_format=export_settings.format,
                       threads=export_settings.threads,
                       key_field=export_settings.key_field,
                       log_file=export_settings.log_file)

    def import_data(self):
        import_file = self.test_config.export_settings.import_file
        if import_file is None:
            import_file = 'data.{}'.format(self.test_config.export_settings.type)
            import_file = os.path.join(self.cluster_spec.backup, import_file)
        if self.test_config.export_settings.format != 'sample':
            import_file = 'file://{}'.format(import_file)

        local.drop_caches()

        export_settings = self.test_config.export_settings

        local.cbimport(master_node=self.master_node,
                       cluster_spec=self.cluster_spec,
                       data_type=export_settings.type,
                       data_format=export_settings.format,
                       bucket=self.test_config.buckets[0],
                       import_file=import_file,
                       threads=export_settings.threads,
                       field_separator=export_settings.field_separator,
                       limit_rows=export_settings.limit_rows,
                       skip_rows=export_settings.skip_rows,
                       infer_types=export_settings.infer_types,
                       omit_empty=export_settings.omit_empty,
                       errors_log=export_settings.errors_log,
                       log_file=export_settings.log_file)

    def _report_kpi(self, time_elapsed: float):
        self.reporter.post(
            *self.metrics.import_and_export_throughput(time_elapsed)
        )


class ExportTest(ExportImportTest):

    @with_stats
    @timeit
    def export(self):
        super().export()

    def run(self):
        super().run()

        time_elapsed = self.export()

        self.report_kpi(time_elapsed)


class ImportTest(ExportImportTest):

    @with_stats
    @timeit
    def import_data(self):
        super().import_data()

    def run(self):
        super().run()

        self.export()

        self.flush_buckets()

        time_elapsed = self.import_data()

        self.report_kpi(time_elapsed)


class ImportSampleDataTest(ImportTest):

    def _report_kpi(self, time_elapsed: float):
        self.reporter.post(
            *self.metrics.import_file_throughput(time_elapsed)
        )

    def run(self):
        self.extract_tools()

        time_elapsed = self.import_data()

        self.report_kpi(time_elapsed)
