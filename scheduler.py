"""
Run: python scheduler.py
Posts 5x/day at times defined in .env (Bangkok timezone).
"""
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config import POST_TIMES, TIMEZONE
from main import run_post_cycle

log = logging.getLogger(__name__)
scheduler = BlockingScheduler(timezone=pytz.timezone(TIMEZONE))


def schedule_posts():
    for time_str in POST_TIMES:
        hour, minute = map(int, time_str.strip().split(":"))
        scheduler.add_job(
            run_post_cycle,
            CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
            id=f"post_{hour:02d}{minute:02d}",
            replace_existing=True,
        )
        log.info(f"Scheduled post at {time_str} Bangkok time")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    schedule_posts()
    log.info(f"Scheduler running — {len(POST_TIMES)} posts/day")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Scheduler stopped")
