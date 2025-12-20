"""
Agent Manager - Orchestrates all agents in the me·an·dus system.

Responsibilities:
- Spawn and monitor all autonomous agents as async tasks
- Create signals when file changes are detected
- Health checks and auto-restart on failure
- Serve the web interface

The agents themselves handle:
- Checking for work (signals, time windows, state)
- Deciding when to do work
- Communicating via signal files
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

# Import autonomous agents
from src.agents.ingestion import AutonomousIngestionAgent
from src.agents.summary import AutonomousSummaryAgent
from src.agents.values import AutonomousValuesAgent
from src.agents.world import AutonomousWorldAgent
from src.agents.attention import AutonomousAttentionAgent


class AutonomousAgentTask:
    """Wrapper for an autonomous agent with management metadata."""

    def __init__(self, agent, restart_on_failure: bool = True):
        self.agent = agent
        self.name = agent.name
        self.restart_on_failure = restart_on_failure
        self.task: Optional[asyncio.Task] = None
        self.started_at: Optional[datetime] = None
        self.error_count: int = 0

    async def start(self):
        """Start the agent's autonomous loop."""
        self.started_at = datetime.now()
        self.task = asyncio.create_task(self._run_with_error_handling())
        logger.info(f"Started autonomous agent: {self.name}")

    async def _run_with_error_handling(self):
        """Run the agent with error handling and restart."""
        while True:
            try:
                await self.agent.run()
            except asyncio.CancelledError:
                logger.info(f"Agent {self.name} cancelled")
                self.agent.stop()
                break
            except Exception as e:
                self.error_count += 1
                logger.error(f"Agent {self.name} error: {e}")
                if self.restart_on_failure:
                    logger.info(f"Restarting {self.name} in 10 seconds...")
                    await asyncio.sleep(10)
                else:
                    break

    def is_running(self) -> bool:
        """Check if the agent is running."""
        return self.task is not None and not self.task.done()

    def cancel(self):
        """Cancel the agent task."""
        if self.task:
            self.task.cancel()

    def get_status(self) -> dict:
        """Get agent status."""
        return {
            "name": self.name,
            "running": self.is_running(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "error_count": self.error_count,
            "work_count": self.agent.work_count if hasattr(self.agent, 'work_count') else 0,
            "last_work": self.agent.last_work_time.isoformat() if hasattr(self.agent, 'last_work_time') and self.agent.last_work_time else None,
            "check_interval": self.agent.check_interval
        }


class InboxHandler(FileSystemEventHandler):
    """Handle new files in the inbox - creates signal for ingestion agent."""

    def on_created(self, event):
        if event.is_directory:
            return
        logger.info(f"New file in inbox: {Path(event.src_path).name}")
        # Create signal file for ingestion agent to pick up
        signal_file = SIGNALS_DIR / "inbox_changed.signal"
        signal_file.write_text(datetime.now().isoformat())


class LogHandler(FileSystemEventHandler):
    """Handle log file changes - creates signal for summary agent."""

    def __init__(self):
        self._last_signal = None

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.md'):
            return
        if '_manifest' in event.src_path or '_summary' in event.src_path:
            return

        # Debounce - don't signal more than once per 5 seconds
        now = datetime.now()
        if self._last_signal and (now - self._last_signal).seconds < 5:
            return

        self._last_signal = now
        logger.info(f"Log changed: {Path(event.src_path).name}")
        # Create signal file for summary agent to pick up
        signal_file = SIGNALS_DIR / "logs_updated.signal"
        signal_file.write_text(now.isoformat())


class AgentManager:
    """
    Central manager for all autonomous agents in the system.

    Handles:
    - Spawning autonomous agent loops
    - File watchers that create signals
    - Health monitoring and auto-restart
    - Web server
    """

    def __init__(self):
        self.agent_tasks: dict[str, AutonomousAgentTask] = {}
        self.observers: list[Observer] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.running = False

    async def start(self):
        """Start the agent manager and all autonomous agents."""
        self.loop = asyncio.get_event_loop()
        self.running = True

        logger.info("=" * 60)
        logger.info("me·an·dus - Agent Manager")
        logger.info("=" * 60)

        # Start file watchers (create signals for agents)
        self._start_watchers()

        # Start the web server
        await self._start_web_server()

        # Spawn all autonomous agents
        await self._spawn_agents()

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
        for task in self.agent_tasks.values():
            task.cancel()

        logger.info("Agent Manager stopped.")

    async def _spawn_agents(self):
        """Spawn all autonomous agents."""
        # Create agent instances
        agents = [
            AutonomousIngestionAgent(),
            AutonomousSummaryAgent(),
            AutonomousValuesAgent(),
            AutonomousWorldAgent(sweep_interval_hours=24),
            AutonomousAttentionAgent(morning_hour=7, evening_hour=21),
        ]

        # Wrap in tasks and start
        for agent in agents:
            task = AutonomousAgentTask(agent)
            self.agent_tasks[agent.name] = task
            await task.start()

        logger.info(f"Spawned {len(agents)} autonomous agents")

    def _start_watchers(self):
        """Start file system watchers that create signals."""
        # Ensure directories exist
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Watch inbox directory
        observer = Observer()
        observer.schedule(InboxHandler(), str(INBOX_DIR), recursive=False)
        observer.start()
        self.observers.append(observer)
        logger.info(f"Watching inbox: {INBOX_DIR}")

        # Watch log directory for changes
        observer = Observer()
        observer.schedule(LogHandler(), str(LOG_DIR), recursive=True)
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

    async def _health_check_loop(self):
        """Monitor agent health and restart if needed."""
        while self.running:
            for name, task in self.agent_tasks.items():
                if not task.is_running() and task.restart_on_failure:
                    logger.warning(f"Agent {name} not running, restarting...")
                    await task.start()

            await asyncio.sleep(30)  # Check every 30 seconds

    # ============== Status ==============

    def get_status(self) -> dict:
        """Get the status of all agents."""
        return {
            "running": self.running,
            "agents": {
                name: task.get_status()
                for name, task in self.agent_tasks.items()
            },
            "watchers": len(self.observers),
            "timestamp": datetime.now().isoformat()
        }

    def get_agent(self, name: str) -> Optional[AutonomousAgentTask]:
        """Get a specific agent task by name."""
        return self.agent_tasks.get(name)


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
