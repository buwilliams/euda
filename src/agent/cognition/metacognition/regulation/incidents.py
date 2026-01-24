"""
Incident Tracking for Token Threshold Breaches

Tracks and stores incidents when agents exceed token thresholds,
allowing operators to review and acknowledge issues.
"""

import json
import threading
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from ....logger import get_logger


DATA_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "data"
INCIDENTS_DIR = DATA_DIR / "system" / "incidents"


class IncidentSeverity(Enum):
    """Incident severity levels."""
    WARNING = "warning"  # Approaching threshold
    CRITICAL = "critical"  # Threshold exceeded, agent paused


class IncidentType(Enum):
    """Types of incidents that can occur."""
    INPUT_THRESHOLD_WARNING = "input_threshold_warning"
    INPUT_THRESHOLD_EXCEEDED = "input_threshold_exceeded"
    OUTPUT_THRESHOLD_WARNING = "output_threshold_warning"
    OUTPUT_THRESHOLD_EXCEEDED = "output_threshold_exceeded"
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    ITERATION_LIMIT_EXCEEDED = "iteration_limit_exceeded"
    RECURSION_LIMIT_EXCEEDED = "recursion_limit_exceeded"


@dataclass
class Incident:
    """An incident record."""
    id: str
    agent_id: str
    incident_type: str
    severity: str
    reason: str
    details: dict
    timestamp: str
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None


class IncidentTracker:
    """Tracks and stores incidents for token threshold breaches.

    Incidents are stored in JSONL files organized by date for easy
    browsing and cleanup. Unacknowledged incidents are also cached
    in memory for fast access.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._logger = get_logger("system/logs/incidents")
        self._unacknowledged: dict = {}  # incident_id -> Incident

        # Load unacknowledged incidents from disk on startup
        self._load_unacknowledged()

    def _load_unacknowledged(self):
        """Load unacknowledged incidents from disk."""
        incidents_file = INCIDENTS_DIR / "unacknowledged.json"
        if incidents_file.exists():
            try:
                with open(incidents_file) as f:
                    data = json.load(f)
                for incident_dict in data:
                    incident = Incident(**incident_dict)
                    self._unacknowledged[incident.id] = incident
            except (json.JSONDecodeError, IOError, TypeError):
                pass

    def _save_unacknowledged(self):
        """Persist unacknowledged incidents to disk."""
        INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)
        incidents_file = INCIDENTS_DIR / "unacknowledged.json"

        incidents_list = [asdict(i) for i in self._unacknowledged.values()]
        with open(incidents_file, "w") as f:
            json.dump(incidents_list, f, indent=2)

    def record(
        self,
        agent_id: str,
        incident_type: IncidentType,
        reason: str,
        severity: IncidentSeverity,
        details: Optional[dict] = None
    ) -> Incident:
        """Record a new incident.

        Args:
            agent_id: ID of the affected agent
            incident_type: Type of incident
            reason: Human-readable reason for the incident
            severity: Incident severity level
            details: Additional details about the incident

        Returns:
            The created Incident
        """
        incident = Incident(
            id=f"inc-{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            incident_type=incident_type.value,
            severity=severity.value,
            reason=reason,
            details=details or {},
            timestamp=datetime.now().isoformat()
        )

        with self._lock:
            # Add to unacknowledged cache
            self._unacknowledged[incident.id] = incident
            self._save_unacknowledged()

            # Also log to JSONL for history
            self._logger.info({
                "event": "incident_recorded",
                **asdict(incident)
            })

        return incident

    def get_unacknowledged(self, agent_id: Optional[str] = None) -> List[Incident]:
        """Get all unacknowledged incidents.

        Args:
            agent_id: Optional filter by agent ID

        Returns:
            List of unacknowledged Incident objects
        """
        with self._lock:
            incidents = list(self._unacknowledged.values())

        if agent_id:
            incidents = [i for i in incidents if i.agent_id == agent_id]

        # Sort by timestamp descending (newest first)
        incidents.sort(key=lambda x: x.timestamp, reverse=True)
        return incidents

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get a specific incident by ID.

        Args:
            incident_id: The incident ID

        Returns:
            Incident or None if not found
        """
        with self._lock:
            return self._unacknowledged.get(incident_id)

    def acknowledge(self, incident_id: str, acknowledged_by: str = "user") -> bool:
        """Acknowledge an incident.

        Args:
            incident_id: ID of the incident to acknowledge
            acknowledged_by: Who acknowledged it (user, cli, api)

        Returns:
            True if acknowledged, False if not found
        """
        with self._lock:
            incident = self._unacknowledged.get(incident_id)
            if not incident:
                return False

            # Update incident
            incident.acknowledged = True
            incident.acknowledged_at = datetime.now().isoformat()
            incident.acknowledged_by = acknowledged_by

            # Remove from unacknowledged cache
            del self._unacknowledged[incident_id]
            self._save_unacknowledged()

            # Log acknowledgment
            self._logger.info({
                "event": "incident_acknowledged",
                "incident_id": incident_id,
                "acknowledged_by": acknowledged_by
            })

        return True

    def acknowledge_all(self, agent_id: Optional[str] = None,
                        acknowledged_by: str = "user") -> int:
        """Acknowledge all incidents for an agent (or all agents).

        Args:
            agent_id: Optional agent ID filter
            acknowledged_by: Who acknowledged them

        Returns:
            Number of incidents acknowledged
        """
        with self._lock:
            to_remove = []
            for incident_id, incident in self._unacknowledged.items():
                if agent_id is None or incident.agent_id == agent_id:
                    incident.acknowledged = True
                    incident.acknowledged_at = datetime.now().isoformat()
                    incident.acknowledged_by = acknowledged_by
                    to_remove.append(incident_id)

            for incident_id in to_remove:
                del self._unacknowledged[incident_id]

            if to_remove:
                self._save_unacknowledged()
                self._logger.info({
                    "event": "incidents_bulk_acknowledged",
                    "count": len(to_remove),
                    "agent_id": agent_id,
                    "acknowledged_by": acknowledged_by
                })

        return len(to_remove)

    def get_history(self, days: int = 7, agent_id: Optional[str] = None) -> List[dict]:
        """Get incident history from logs.

        Args:
            days: Number of days of history
            agent_id: Optional filter by agent ID

        Returns:
            List of incident dicts from log history
        """
        logs = self._logger.read_logs(days=days)
        incidents = [
            log for log in logs
            if log.get("event") == "incident_recorded"
        ]

        if agent_id:
            incidents = [i for i in incidents if i.get("agent_id") == agent_id]

        return incidents


# Singleton instance
_tracker: Optional[IncidentTracker] = None
_tracker_lock = threading.Lock()


def get_incident_tracker() -> IncidentTracker:
    """Get the global IncidentTracker instance."""
    global _tracker
    with _tracker_lock:
        if _tracker is None:
            _tracker = IncidentTracker()
        return _tracker
