'''
Post-Release Updates:
'''

import multiprocessing

from local_source_paths import prefer_local_solving_source


LOCAL_SOLVING_SOURCE = prefer_local_solving_source()


def main():
    from app_gui import main as run_app

    run_app()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
