# src/app/services/policy_scheduler_service.py
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Optional
import time

from app.db.session import SessionLocal
from app.services.policy_agent_service import run_policy_agent
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PolicySchedulerService:
    """
    Background scheduler service that automatically runs the AI Policy Agent
    at regular intervals to evaluate rules and send emails.
    """
    
    def __init__(self, interval_minutes: int = 30):
        """
        Initialize the scheduler.
        
        Args:
            interval_minutes: How often to run the policy agent (default: 30 minutes)
        """
        self.interval_minutes = interval_minutes
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    def start(self):
        """Start the background scheduler."""
        if self.is_running:
            logger.warning("Policy scheduler is already running")
            return
            
        logger.info(f"🤖 Starting AI Policy Agent scheduler (interval: {self.interval_minutes} minutes)")
        
        self.is_running = True
        self.stop_event.clear()
        
        # Start the scheduler in a separate thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ Policy scheduler started successfully")
    
    def stop(self):
        """Stop the background scheduler."""
        if not self.is_running:
            return
            
        logger.info("🛑 Stopping AI Policy Agent scheduler...")
        
        self.is_running = False
        self.stop_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
            
        logger.info("✅ Policy scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop that runs in a separate thread."""
        logger.info("🔄 Policy scheduler loop started")
        
        # Run immediately on startup
        asyncio.run(self._execute_policy_agent())
        
        while not self.stop_event.is_set():
            try:
                # Wait for the specified interval or until stop event
                if self.stop_event.wait(timeout=self.interval_minutes * 60):
                    break  # Stop event was set
                
                # Run the policy agent
                asyncio.run(self._execute_policy_agent())
                
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {str(e)}")
                # Continue running even if there's an error
                time.sleep(60)  # Wait 1 minute before retrying
    
    async def _execute_policy_agent(self):
        """Execute the policy agent and log results."""
        try:
            execution_time = datetime.now()
            logger.info(f"⏰ Executing scheduled policy agent run at {execution_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            db = SessionLocal()
            try:
                results = await run_policy_agent(db)
                
                # Log execution results
                logger.info("📊 Scheduled Policy Agent Results:")
                logger.info(f"   - Rules evaluated: {results['total_rules']}")
                logger.info(f"   - Customers checked: {results['total_customers']}")
                logger.info(f"   - Matches found: {results['matches_found']}")
                logger.info(f"   - Emails sent: {results['actions_executed']}")
                logger.info(f"   - Errors: {results['errors']}")
                
                # Log details for each rule
                for detail in results.get('details', []):
                    if detail['matches'] > 0:
                        logger.info(f"   📋 {detail['rule_name']}: {detail['matches']} matches, {detail['actions_executed']} emails sent")
                
                if results['actions_executed'] > 0:
                    logger.info(f"✅ Scheduled execution completed: {results['actions_executed']} automated emails sent")
                else:
                    logger.info("ℹ️ Scheduled execution completed: No actions required")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error executing scheduled policy agent: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_status(self) -> dict:
        """Get the current status of the scheduler."""
        return {
            "is_running": self.is_running,
            "interval_minutes": self.interval_minutes,
            "thread_alive": self.scheduler_thread.is_alive() if self.scheduler_thread else False
        }


# Global scheduler instance
_policy_scheduler: Optional[PolicySchedulerService] = None


def start_policy_scheduler(interval_minutes: int = 30):
    """
    Start the global policy scheduler.
    
    Args:
        interval_minutes: How often to run the policy agent (default: 30 minutes)
    """
    global _policy_scheduler
    
    if _policy_scheduler and _policy_scheduler.is_running:
        logger.warning("Policy scheduler is already running")
        return _policy_scheduler
    
    _policy_scheduler = PolicySchedulerService(interval_minutes)
    _policy_scheduler.start()
    return _policy_scheduler


def stop_policy_scheduler():
    """Stop the global policy scheduler."""
    global _policy_scheduler
    
    if _policy_scheduler:
        _policy_scheduler.stop()
        _policy_scheduler = None


def get_policy_scheduler() -> Optional[PolicySchedulerService]:
    """Get the current policy scheduler instance."""
    return _policy_scheduler


def get_scheduler_status() -> dict:
    """Get the status of the policy scheduler."""
    if _policy_scheduler:
        return _policy_scheduler.get_status()
    else:
        return {
            "is_running": False,
            "interval_minutes": None,
            "thread_alive": False
        }
