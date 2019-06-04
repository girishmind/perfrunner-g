import os
import sys
from argparse import ArgumentParser

import requests

from logger import logger

BASE_URL = 'http://172.23.120.24/builds/latestbuilds/couchbase-server'

CHECKPOINT_DIR = '/home/'

MAX_MISSING = 3

RELEASES = {
    'spock': '5.0.0',
    'vulcan': '5.5.0',
    'alice': '6.0.0',
    'mad-hatter': '6.5.0'
}


def read_latest(release: str) -> int:
    checkpoint = os.path.join(CHECKPOINT_DIR, release)
    with open(checkpoint) as f:
        build = f.read()
        return int(build)


def store_latest(release: str, build: int):
    logger.info('Storing build {}'.format(build))

    checkpoint = os.path.join(CHECKPOINT_DIR, release)
    with open(checkpoint, 'w') as f:
        f.write(str(build))


def build_exists(release: str, build: str) -> bool:
    url = '{}/{release}/{build}/'.format(BASE_URL, release=release, build=build)

    r = requests.head(url)
    return r.status_code == 200


def rpm_package_exists(release: str, build: str) -> bool:
    semver = RELEASES[release]
    package = 'couchbase-server-enterprise-{semver}-{build}-centos7.x86_64.rpm'\
        .format(semver=semver, build=build)
    url = '{}/{release}/{build}/{package}'.format(
        BASE_URL, release=release, build=build, package=package)

    r = requests.head(url)
    return r.status_code == 200


def get_args():
    parser = ArgumentParser()

    parser.add_argument('-r', '--release', dest='release', default='spock')

    return parser.parse_args()


def main():
    args = get_args()

    latest = None
    build = read_latest(release=args.release)
    missing = 0

    while missing < MAX_MISSING:
        build += 1

        logger.info('Checking build {}'.format(build))

        if not build_exists(args.release, build):
            missing += 1
            continue

        if rpm_package_exists(args.release, build):
            latest = build

    if latest:
        store_latest(release=args.release, build=latest)
    else:
        sys.exit('No new build found')


if __name__ == '__main__':
    main()
