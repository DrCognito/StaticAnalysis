from argparse import ArgumentParser, BooleanOptionalAction
#
from os import rename
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

import StaticAnalysis
from StaticAnalysis import session
from StaticAnalysis.replays.Replay import InitDB, populate_from_JSON_file
from StaticAnalysis.lib.metadata import has_picks

import time
from datetime import timedelta
from statistics import fmean

from loguru import logger as LOG

# Main
json_set = StaticAnalysis.CONFIG['json']
# Testing
# json_set = StaticAnalysis.CONFIG['json']['test']

PROCESSING_PATH = json_set['JSON_PATH']
ARCHIVE_PATH = json_set['JSON_ARCHIVE']
DRAFT_PROCESSING_PATH = json_set['DRAFT_JSON_PATH']
DRAFT_ARCHIVE_PATH = json_set['DRAFT_JSON_ARCHIVE']


def drafts_to_db(skip_existing=True, json_files:list[Path]=[]):
    # json_files = list(Path(base_path).glob('*.json'))
    for j in json_files:
        LOG.info(j)
        archive = Path(DRAFT_ARCHIVE_PATH) / j.name
        if archive.exists():
            LOG.info(f"File already processed and exists in archive! {archive}")
            continue
        try:
            populate_from_JSON_file(j, session, skip_existing)
        except SQLAlchemyError as e:
            LOG.opt(exception=True).error("Failed to process {}".format(j))
            session.rollback()
            exit(2)
        except IOError as e:
            LOG.opt(exception=True).error("IOError reading {}".format(j))
            session.rollback()
            exit(3)
        if not archive.exists():
            rename(j, archive)
    session.commit()


def processing_to_db(skip_existing=True, json_files:list[Path]=[], limit=None):
    replays_start = time.perf_counter()
    replay_times = []
    # json_files = list(Path(base_path).glob('*.json'))
    for j in json_files[:limit]:
        j_start = time.perf_counter()

        archive = Path(ARCHIVE_PATH) / j.name
        if archive.exists():
            LOG.info(f"File already processed and exists in archive! {archive}")
            continue
        try:
            populate_from_JSON_file(j, session, skip_existing=skip_existing)
        except SQLAlchemyError as e:
            LOG.opt(exception=True).error("Failed to process {}".format(j))
            session.rollback()
            exit(2)
        except IOError as e:
            LOG.opt(exception=True).error("IOError reading {}".format(j))
            session.rollback()
            exit(3)
        if not archive.exists():
            rename(j, archive)

        LOG.info(f"{j} ({time.perf_counter() - j_start})")
        replay_times.append(time.perf_counter() - j_start)

    if replay_times:
        LOG.info(
            f"Average time per replay: {fmean(replay_times)}. Maximum: {max(replay_times)}"
        )
    total_seconds = time.perf_counter() - replays_start
    LOG.info(f"Total time taken: {timedelta(seconds = total_seconds)}")
    session.commit()


def reprocess_replay(replays):
    for r in replays:
        file = str(r) + '.json'

        process_file = Path(ARCHIVE_PATH) / file
        if process_file.exists():
            LOG.info("Reprocessing ", process_file)
            try:
                populate_from_JSON_file(process_file, session, skip_existing=False)
            except SQLAlchemyError as e:
                LOG.opt(exception=True).error("Failed to process {}".format(j))
                session.rollback()
                exit(2)
            except IOError as e:
                LOG.opt(exception=True).error("IOError reading {}".format(j))
                session.rollback()
                exit(3)
        session.commit()



arguments = ArgumentParser()
arguments.add_argument('--full_reprocess',
                       help='''Reprocesses ALL replays in archive''',
                       action='store_true')
arguments.add_argument('--reprocess_replay',
                       help='''Reprocess specific replays, supports lists''',
                       nargs='*')
arguments.add_argument('--limit',
                       help='''Limit number of replays to process''',
                       type=int)
arguments.add_argument("--process_drafts", action=BooleanOptionalAction,
                       default=True)
arguments.add_argument("--skip_existing", action=BooleanOptionalAction,
                       default=False)


if __name__ == '__main__':
    args = arguments.parse_args()


    if args.reprocess_replay is not None:
        reprocess_replay(args.reprocess_replay)

    skip_existing = args.skip_existing
    json_files = list(Path(PROCESSING_PATH).glob('*.json'))
    archive_files = list(Path(ARCHIVE_PATH).glob('*.json'))

    if args.full_reprocess:
        skip_existing = False
        json_files += archive_files

    processing_to_db(limit=args.limit, json_files=json_files, skip_existing=skip_existing)

    if args.process_drafts:
        # Get a list of drafts and see if we have the full process already
        # drafts_to_db(skip_existing=False, base_path=DRAFT_PROCESSING_PATH)
        file_names = {f.name for f in json_files}
        json_draft = []
        for j in list(Path(DRAFT_PROCESSING_PATH).glob('*.json')):
            if j.name in file_names:
                LOG.info(f"Skipping draft for {j.name} as it has a full replay in processing.")
                archive = Path(DRAFT_ARCHIVE_PATH) / j.name
                rename(j, archive)
                continue
            if j.name in archive_files:
                LOG.info(f"Skipping draft for {j.name} as it has a full replay in archive.")
                archive = Path(DRAFT_ARCHIVE_PATH) / j.name
                rename(j, archive)
                continue

            json_draft.append(j)

        # And cover reprocessing (same but with no rename)
        if args.full_reprocess:
            for j in list(Path(DRAFT_ARCHIVE_PATH).glob('*.json')):
                if j.name in file_names:
                    LOG.info(f"Skipping draft for {j.name} as it has a full replay.")
                    continue

                json_draft.append(j)

        drafts_to_db(skip_existing=skip_existing, json_files=json_draft)



