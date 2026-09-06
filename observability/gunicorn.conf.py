"""gunicorn config for Prometheus multiprocess mode.

PROMETHEUS_MULTIPROC_DIR is set in the compose command (shell), not here, so it
propagates to forked workers. This hook cleans up live-mode gauge files when a
worker exits. NOTE: counter/histogram .db files persist per-PID by design and
accumulate on worker recycle (--max-requests); the dir is tmpfs-backed so it
clears on container restart. See the README observability notes.
"""

from prometheus_client import multiprocess


def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid)
