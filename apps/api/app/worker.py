import dramatiq
from dramatiq.brokers.redis import RedisBroker
from .config import settings
from .orchestrator import run_analysis

dramatiq.set_broker(RedisBroker(url=settings.redis_url))

@dramatiq.actor(max_retries=2, min_backoff=1000, max_backoff=30000)
def analyze_incident(run_id: str):
    run_analysis(run_id)
