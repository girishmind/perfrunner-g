import glob
import zipfile
from collections import defaultdict
from typing import List

from logger import logger
from perfrunner.helpers.misc import pretty_dict

GOLANG_LOG_FILES = ("eventing.log",
                    "fts.log",
                    "goxdcr.log",
                    "indexer.log",
                    "projector.log",
                    "query.log")


def check_for_golang_panic(file_name: str) -> List[str]:
    zf = zipfile.ZipFile(file_name)
    panic_files = []
    for name in zf.namelist():
        if any(log_file in name for log_file in GOLANG_LOG_FILES):
            data = zf.read(name)
            if "panic" in str(data):
                panic_files.append(name)
    return panic_files


def check_for_crash_files(file_name: str) -> List[str]:
    zf = zipfile.ZipFile(file_name)
    crash_files = []
    for name in zf.namelist():
        if name.endswith('.dmp'):
            crash_files.append(name)
    return crash_files


def validate_logs(file_name: str):
    panic_files = check_for_golang_panic(file_name)
    crash_files = check_for_crash_files(file_name)
    return panic_files, crash_files


def main():
    failures = defaultdict(dict)

    for file_name in glob.iglob('./*.zip'):
        panic_files, crash_files = validate_logs(file_name)
        if panic_files:
            failures['panics'][file_name] = panic_files
        if crash_files:
            failures['crashes'][file_name] = crash_files

    if failures:
        logger.interrupt(
            "Following failures found: {}".format(pretty_dict(failures)))


if __name__ == '__main__':
    main()
