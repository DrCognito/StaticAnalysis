from argparse import ArgumentParser, BooleanOptionalAction
from os import environ as environment
from os import rename
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from StaticAnalysis.replays.Replay import InitDB, populate_from_JSON_file

DB_PATH = environment['PARSED_DB_PATH']
PROCESSING_PATH = environment['JSON_PATH']
ARCHIVE_PATH = environment['JSON_ARCHIVE']

DRAFT_PROCESSING_PATH = environment['DRAFT_JSON_PATH']
DRAFT_ARCHIVE_PATH = environment['DRAFT_JSON_ARCHIVE']

engine = InitDB(DB_PATH)
Session = sessionmaker(bind=engine)
session = Session()


def drafts_to_db(skip_existing=True, base_path=DRAFT_PROCESSING_PATH):
    json_files = list(Path(base_path).glob('*.json'))
    for j in json_files:
        print(j)
        archive = Path(DRAFT_ARCHIVE_PATH) / j.name
        if archive.exists():
            print(f"File already processed and exists in archive! {archive}")
            continue
        try:
            populate_from_JSON_file(j, session, skip_existing)
        except SQLAlchemyError as e:
            print(e)
            print("Failed to process {}".format(j))
            session.rollback()
            exit(2)
        except IOError as e:
            print(e)
            print("IOError reading {}".format(j))
            session.rollback()
            exit(3)
        if base_path != Path(DRAFT_ARCHIVE_PATH):
            rename(j, Path(DRAFT_ARCHIVE_PATH) / j.name)
    session.commit()


def processing_to_db(skip_existing=True, base_path=PROCESSING_PATH, limit=None):
    json_files = list(Path(base_path).glob('*.json'))
    for j in json_files[:limit]:
        print(j)
        archive = Path(ARCHIVE_PATH) / j.name
        if archive.exists():
            print(f"File already processed and exists in archive! {archive}")
            continue
        try:
            populate_from_JSON_file(j, session, skip_existing=skip_existing)
        except SQLAlchemyError as e:
            print(e)
            print("Failed to process {}".format(j))
            session.rollback()
            exit(2)
        except IOError as e:
            print(e)
            print("IOError reading {}".format(j))
            session.rollback()
            exit(3)
        if base_path != Path(ARCHIVE_PATH):
            rename(j, Path(ARCHIVE_PATH) / j.name)
    session.commit()


def reprocess_replay(replays):
    for r in replays:
        file = str(r) + '.json'

        process_file = Path(ARCHIVE_PATH) / file
        if process_file.exists():
            print("Reprocessing ", process_file)
            try:
                populate_from_JSON_file(process_file, session, skip_existing=False)
            except SQLAlchemyError as e:
                print(e)
                print("Failed to process {}".format(j))
                session.rollback()
                exit(2)
            except IOError as e:
                print(e)
                print("IOError reading {}".format(j))
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


if __name__ == '__main__':
    args = arguments.parse_args()

    if args.process_drafts:
        drafts_to_db(skip_existing=False, base_path=DRAFT_PROCESSING_PATH)

    if args.reprocess_replay is not None:
        reprocess_replay(args.reprocess_replay)

    if args.full_reprocess:
        processing_to_db(skip_existing=False,
                         base_path=ARCHIVE_PATH,
                         limit=args.limit)
        exit()

    processing_to_db(limit=args.limit, skip_existing=False)
