"""
Agent Manager - Orchestrates all agents in the Me and Us system.

Responsibilities:
- Spawn and monitor all agents as async tasks
- Trigger agents on schedules (morning, evening, weekly)
- Trigger agents on file changes (inbox, logs, summaries)
- Handle inter-agent signaling via signal files
- Health checks and auto-restart on failure
"""

import asyncio
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('manager')

# Base paths
DATA_DIR = Path(__file__).parent.parent / "data"
SIGNALS_DIR = DATA_DIR / "agents" / "signals"
INBOX_DIR = DATA_DIR / "inbox" / "pending"
LOG_DIR = DATA_DIR / "log"

# Ensure directories exist
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)


class AgentTask:
    """Wrapper for an agent task with metadata."""

    def __init__(self, name: str, run_func: Callable, restart_on_failure: bool = True):
        self.name = name
        self.run_func = run_func
        self.restart_on_failure = restart_on_failure
        self.task: Optional[asyncio.Task] = None
        self.last_run: Optional[datetime] = None
        self.run_count: int = 0
        self.error_count: int = 0

    async def start(self):
        """Start the agent task."""
        self.task = asyncio.create_task(self._run_with_error_handling())
        logger.info(f"Started agent: {self.name}")

    async def _run_with_error_handling(self):
        """Run the agent with error handling."""
        while True:
            try:
                self.last_run = datetime.now()
                self.run_count += 1
                await self.run_func()
            except asyncio.CancelledError:
                logger.info(f"Agent {self.name} cancelled")
                break
            except Exception as e:
                self.error_count += 1
                logger.error(f"Agent {self.name} error: {e}")
                if self.restart_on_failure:
                    logger.info(f"Restarting {self.name} in 5 seconds...")
                    await asyncio.sleep(5)
                else:
                    break

    def is_running(self) -> bool:
        """Check if the agent is running."""
        return self.task is not None and not self.task.done()

    def cancel(self):
        """Cancel the agent task."""
        if self.task:
            self.task.cancel()


class SignalHandler(FileSystemEventHandler):
    """Handle signal file events for inter-agent communication."""

    def __init__(self, manager: 'AgentManager'):
        self.manager = manager

    def on_created(self, event):
        if event.is_directory:
            return
        signal_name = Path(event.src_path).stem
        logger.info(f"Signal received: {signal_name}")
        asyncio.run_coroutine_threadsafe(
            self.manager.handle_signal(signal_name),
            self.manager.loop
        )


class InboxHandler(FileSystemEventHandler):
    """Handle new files in the inbox."""

    def __init__(self, manager: 'AgentManager'):
        self.manager = manager

    def on_created(self, event):
        if event.is_directory:
            return
        logger.info(f"New file in inbox: {Path(event.src_path).name}")
        asyncio.run_coroutine_threadsafe(
            self.manager.trigger_ingestion(),
            self.manager.loop
        )


class LogHandler(FileSystemEventHandler):
    """Handle log file changes to trigger summary updates."""

    def __init__(self, manager: 'AgentManager'):
        self.manager = manager
        self._debounce_task = None

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.md'):
            return
        if '_manifest' in event.src_path or '_summary' in event.src_path:
            return

        # Debounce - wait for writes to settle
        asyncio.run_coroutine_threadsafe(
            self.manager.schedule_summary_check(),
            self.manager.loop
        )


class AgentManager:
    """
    Central manager for all agents in the system.

    Handles:
    - Starting/stopping agents
    - File watchers for triggers
    - Scheduled tasks (morning, evening, weekly)
    - Inter-agent signaling
    - Health monitoring
    """

    def __init__(self):
        self.agents: dict[str, AgentTask] = {}
        self.observers: list[Observer] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.running = False
        self._summary_check_scheduled = False
        self._schedule_config = {
            'morning_hour': 7,
            'morning_minute': 0,
            'evening_hour': 21,
            'evening_minute': 0,
            'weekly_day': 6,  # Sunday
            'weekly_hour': 10,
        }

    async def start(self):
        """Start the agent manager and all agents."""
        self.loop = asyncio.get_event_loop()
        self.running = True

        logger.info("=" * 60)
        logger.info("Me and Us - Agent Manager")
        logger.info("=" * 60)

        # Start file watchers
        self._start_watchers()

        # Start the web server as a background task
        await self._start_web_server()

        # Start scheduled task checker
        asyncio.create_task(self._schedule_loop())

        # Start health check loop
        asyncio.create_task(self._health_check_loop())

        logger.info("Agent Manager running. Press Ctrl+C to stop.")

        # Keep running
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def stop(self):
        """Stop all agents and watchers."""
        logger.info("Stopping Agent Manager...")
        self.running = False

        # Stop file watchers
        for observer in self.observers:
            observer.stop()
            observer.join()

        # Cancel all agent tasks
        for agent in self.agents.values():
            agent.cancel()

        logger.info("Agent Manager stopped.")

    def _start_watchers(self):
        """Start file system watchers."""
        # Watch signals directory
        if SIGNALS_DIR.exists():
            observer = Observer()
            observer.schedule(SignalHandler(self), str(SIGNALS_DIR), recursive=False)
            observer.start()
            self.observers.append(observer)
            logger.info(f"Watching signals: {SIGNALS_DIR}")

        # Watch inbox directory
        if INBOX_DIR.exists():
            observer = Observer()
            observer.schedule(InboxHandler(self), str(INBOX_DIR), recursive=False)
            observer.start()
            self.observers.append(observer)
            logger.info(f"Watching inbox: {INBOX_DIR}")

        # Watch log directory for changes
        if LOG_DIR.exists():
            observer = Observer()
            observer.schedule(LogHandler(self), str(LOG_DIR), recursive=True)
            observer.start()
            self.observers.append(observer)
            logger.info(f"Watching logs: {LOG_DIR}")

    async def _start_web_server(self):
        """Start the FastAPI web server."""
        import uvicorn

        config = uvicorn.Config(
            "src.web.app:app",
            host="0.0.0.0",
            port=8000,
            log_level="warning",
            access_log=False
        )
        server = uvicorn.Server(config)

        # Run server in background
        asyncio.create_task(server.serve())
        logger.info("Web server started at http://localhost:8000")

    async def _schedule_loop(self):
        """Check for scheduled tasks."""
        last_morning = None
        last_evening = None
        last_weekly = None

        while self.running:
            now = datetime.now()

            # Morning attention
            morning_time = time(
                self._schedule_config['morning_hour'],
                self._schedule_config['morning_minute']
            )
            if (now.time() >= morning_time and
                (last_morning is None or last_morning.date() < now.date())):
                last_morning = now
                await self.run_morning_attention()

            # Evening reflection
            evening_time = time(
                self._schedule_config['evening_hour'],
                self._schedule_config['evening_minute']
            )
            if (now.time() >= evening_time and
                (last_evening is None or last_evening.date() < now.date())):
                last_evening = now
                await self.run_evening_reflection()

            # Weekly review (Sunday at configured hour)
            if (now.weekday() == self._schedule_config['weekly_day'] and
                now.hour >= self._schedule_config['weekly_hour'] and
                (last_weekly is None or (now - last_weekly).days >= 6)):
                last_weekly = now
                await self.run_weekly_review()

            await asyncio.sleep(60)  # Check every minute

    async def _health_check_loop(self):
        """Monitor agent health and restart if needed."""
        while self.running:
            for name, agent in self.agents.items():
                if not agent.is_running() and agent.restart_on_failure:
                    logger.warning(f"Agent {name} not running, restarting...")
                    await agent.start()

            await asyncio.sleep(30)  # Check every 30 seconds

    # ============== Agent Triggers ==============

    async def trigger_ingestion(self):
        """Trigger the ingestion agent to process inbox files."""
        logger.info("Triggering ingestion agent...")
        try:
            from src.watcher import process_pending
            await asyncio.to_thread(process_pending)
            logger.info("Ingestion complete")
        except Exception as e:
            logger.error(f"Ingestion error: {e}")

    async def schedule_summary_check(self):
        """Schedule a summary check (debounced)."""
        if self._summary_check_scheduled:
            return

        self._summary_check_scheduled = True
        await asyncio.sleep(5)  # Wait for writes to settle
        self._summary_check_scheduled = False

        await self.trigger_summary()

    async def trigger_summary(self):
        """Trigger the summary agent to check for updates needed."""
        logger.info("Checking if summaries need updating...")
        try:
            from src.agents.summary import check_and_summarize_all
            result = await asyncio.to_thread(check_and_summarize_all)
            if result:
                logger.info("Summaries updated, signaling values agent")
                await self.send_signal("summaries_updated")
        except Exception as e:
            logger.error(f"Summary error: {e}")

    async def trigger_values(self):
        """Trigger the values agent to derive values from summaries."""
        logger.info("Triggering values derivation...")
        try:
            from src.agents.values import derive_values
            await asyncio.to_thread(derive_values)
            logger.info("Values updated, signaling world agent")
            await self.send_signal("values_updated")
        except Exception as e:
            logger.error(f"Values error: {e}")

    async def trigger_discovery(self):
        """Trigger the world agent to discover opportunities."""
        logger.info("Running discovery sweep...")
        try:
            from src.agents.world import run_discovery_sweep
            await asyncio.to_thread(run_discovery_sweep)
            logger.info("Discovery complete")
        except Exception as e:
            logger.error(f"Discovery error: {e}")

    async def run_morning_attention(self):
        """Run the morning attention routine."""
        logger.info("Generating morning attention...")
        try:
            from src.agents.attention import morning_attention
            result = await asyncio.to_thread(morning_attention)
            logger.info("Morning attention generated")
            # TODO: Send notification
        except Exception as e:
            logger.error(f"Morning attention error: {e}")

    async def run_evening_reflection(self):
        """Run the evening reflection routine."""
        logger.info("Generating evening reflection...")
        try:
            from src.agents.attention import evening_attention
            result = await asyncio.to_thread(evening_attention)
            logger.info("Evening reflection generated")
            # TODO: Send notification
        except Exception as e:
            logger.error(f"Evening reflection error: {e}")

    async def run_weekly_review(self):
        """Run the weekly review routine."""
        logger.info("Generating weekly review...")
        # TODO: Implement weekly review agent function
        logger.info("Weekly review not yet implemented")

    # ============== Signaling ==============

    async def send_signal(self, signal_name: str):
        """Send a signal to other agents by creating a signal file."""
        signal_file = SIGNALS_DIR / f"{signal_name}.signal"
        signal_file.write_text(datetime.now().isoformat())
        logger.info(f"Signal sent: {signal_name}")

    async def handle_signal(self, signal_name: str):
        """Handle a received signal."""
        signal_file = SIGNALS_DIR / f"{signal_name}.signal"

        # Remove the signal file
        if signal_file.exists():
            signal_file.unlink()

        # Route to appropriate handler
        if signal_name == "summaries_updated":
            await self.trigger_values()
        elif signal_name == "values_updated":
            await self.trigger_discovery()
        elif signal_name == "process_inbox":
            await self.trigger_ingestion()
        else:
            logger.warning(f"Unknown signal: {signal_name}")

    # ============== Status ==============

    def get_status(self) -> dict:
        """Get the status of all agents."""
        return {
            "running": self.running,
            "agents": {
                name: {
                    "running": agent.is_running(),
                    "last_run": agent.last_run.isoformat() if agent.last_run else None,
                    "run_count": agent.run_count,
                    "error_count": agent.error_count
                }
                for name, agent in self.agents.items()
            },
            "watchers": len(self.observers),
            "timestamp": datetime.now().isoformat()
        }


async def run_manager():
    """Run the agent manager."""
    manager = AgentManager()
    try:
        await manager.start()
    except KeyboardInterrupt:
        await manager.stop()


def start():
    """Entry point for starting the agent manager."""
    asyncio.run(run_manager())


if __name__ == "__main__":
    start()
