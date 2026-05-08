import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

import glob, shutil
from main import run_post_cycle, run_video_cycle, run_trend_cycle


def _cleanup_outputs():
    """Delete generated clips/images older than 1 day to free disk space."""
    import time
    cutoff = time.time() - 86400
    removed = 0
    for pattern in ["assets/output/*.mp4", "assets/output/*.jpg", "assets/output/*.png",
                    "assets/output/*.mp3", "assets/output/*.vo.path"]:
        for f in glob.glob(pattern):
            if os.path.getmtime(f) < cutoff:
                try:
                    os.unlink(f)
                    removed += 1
                except Exception:
                    pass
    log.info("[cleanup] removed %d old output files", removed)

BANGKOK = pytz.timezone("Asia/Bangkok")

os.makedirs("logs", exist_ok=True)

log = logging.getLogger("fashionbot")
log.setLevel(logging.INFO)

_fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

_fh = logging.FileHandler("logs/fashionbot.log")
_fh.setFormatter(_fmt)
log.addHandler(_fh)

_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)
log.addHandler(_sh)


def _run_with_log(name, fn):
    log.info(f"[scheduler] Starting {name}")
    try:
        fn()
        log.info(f"[scheduler] {name} complete")
    except Exception as e:
        log.error(f"[scheduler] {name} failed: {e}")


scheduler = BlockingScheduler(timezone=BANGKOK)
scheduler.add_job(
    lambda: _run_with_log("run_post_cycle", run_post_cycle),
    CronTrigger(hour="8,12,18,21", minute=0, timezone=BANGKOK),
)
scheduler.add_job(
    lambda: _run_with_log("run_video_cycle", run_video_cycle),
    CronTrigger(hour="9,15,20", minute=0, timezone=BANGKOK),
)
scheduler.add_job(
    lambda: _run_with_log("run_trend_cycle", run_trend_cycle),
    CronTrigger(hour="*/6", minute=0, timezone=BANGKOK),
)
scheduler.add_job(
    lambda: _run_with_log("cleanup_outputs", _cleanup_outputs),
    CronTrigger(hour=3, minute=0, timezone=BANGKOK),  # 3am Bangkok daily
)

if __name__ == "__main__":
    log.info("[scheduler] Starting scheduler (Bangkok peak-hour posting)")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()
        log.info("[scheduler] Scheduler stopped")
