# src/app/services/policy_scheduler_service.py
import time
import threading
from app.db.session import SessionLocal
from app.services.policy_agent_service import PolicyAgentService
from app.utils.logging import get_logger

logger = get_logger(__name__)

class PolicyScheduler:
    def __init__(self, interval_minutes: float):
        self.interval_seconds = interval_minutes * 60
        self._stop_event = threading.Event()
        self._thread = None
        self.is_running = False

    def start(self):
        if self._thread and self._thread.is_alive():
            logger.warning("Policy scheduler is already running.")
            return
        
        logger.info(f"Starting policy scheduler to run every {self.interval_seconds/60:.1f} minutes.")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.is_running = True

    def stop(self):
        if not self.is_running:
            logger.warning("Policy scheduler is not running.")
            return
            
        logger.info("Stopping policy scheduler.")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)  # Wait up to 5 seconds
        self.is_running = False

    def _run(self):
        logger.info("🤖 Policy scheduler thread started.")
        while not self._stop_event.is_set():
            try:
                with SessionLocal() as db:
                    agent = PolicyAgentService(db)
                    result = agent.run_agent()
                    logger.info(f"Policy agent run completed: {result}")
            except Exception as e:
                logger.error(f"An error occurred in the policy scheduler run: {e}", exc_info=True)
            
            # Wait for the next interval or until stop event is set
            self._stop_event.wait(self.interval_seconds)
        
        logger.info("🛑 Policy scheduler thread stopped.")

# Global instance
scheduler: PolicyScheduler = None

def start_policy_scheduler(interval_minutes: float = 1.0):
    """Start the policy scheduler with the given interval."""
    global scheduler
    
    if interval_minutes <= 0:
        logger.warning("Policy agent interval is set to 0 or negative. Scheduler will not start.")
        return None
    
    # Stop existing scheduler if running
    if scheduler and scheduler.is_running:
        stop_policy_scheduler()
    
    scheduler = PolicyScheduler(interval_minutes=interval_minutes)
    scheduler.start()
    return scheduler

def stop_policy_scheduler():
    """Stop the policy scheduler."""
    global scheduler
    if scheduler:
        scheduler.stop()
        scheduler = None

def get_scheduler_status():
    """Get the current status of the policy scheduler."""
    global scheduler
    if scheduler:
        return {
            "is_running": scheduler.is_running,
            "interval_minutes": scheduler.interval_seconds / 60,
            "thread_alive": scheduler._thread.is_alive() if scheduler._thread else False
        }
    else:
        return {
            "is_running": False,
            "interval_minutes": 0,
            "thread_alive": False
        }