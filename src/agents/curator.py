"""
Curator Agent - The Curator

Decides what deserves attention right now. Explores integrable opportunities,
allocates scarce attention, respects user capacity.

Handles proactive attention - surfacing questions and guidance to help
the user configure and understand the system.

Can emit profile observations for Profiler Agent to integrate (behavioral
patterns around attention, energy, and engagement).
"""

import json
from datetime import datetime, time, timedelta
from pathlib import Path
from .base import create_agent, AutonomousAgent, load_prompt
from ..tools.curator.attention import ATTENTION_TOOLS, ATTENTION_HANDLERS
from ..tools.profiler import PROFILE_TOOLS, PROFILE_HANDLERS
from ..tools.shared.log import LOG_TOOLS, LOG_HANDLERS
from ..tools.shared.notifications import create_euno_task
from ..tools.shared.profile_signals import PROFILE_SIGNAL_TOOLS, PROFILE_SIGNAL_HANDLERS
from ..tools.shared.content_hash import (
    compute_directory_hash, load_cached_hash, save_cached_hash
)

# Paths for proactive attention
DATA_DIR = Path(__file__).parent.parent.parent / "data"
SIGNALS_DIR = DATA_DIR / "shared" / "state" / "signals"
CURATOR_STATE_DIR = DATA_DIR / "curator" / "state"
LIFELOG_DIR = DATA_DIR / "shared" / "state" / "lifelog"
PATTERNS_CACHE_FILE = CURATOR_STATE_DIR / "patterns.cache.json"
CURATOR_STATE_DIR.mkdir(parents=True, exist_ok=True)


# Combined tools - Curator agent needs access to profile and logs
ALL_TOOLS = ATTENTION_TOOLS + PROFILE_TOOLS + LOG_TOOLS + PROFILE_SIGNAL_TOOLS
ALL_HANDLERS = {**ATTENTION_HANDLERS, **PROFILE_HANDLERS, **LOG_HANDLERS, **PROFILE_SIGNAL_HANDLERS}


def create_curator_agent():
    """Create a Curator Agent instance."""
    return create_agent(
        persona_name="curator",
        tools=ALL_TOOLS
    )


def run_interactive():
    """Run an interactive session with the Curator Agent."""
    print("=" * 60)
    print("Euno - Curator Agent")
    print("=" * 60)
    print("\nI decide what deserves your attention right now.")
    print("Commands:")
    print("  - 'morning' - Generate morning attention")
    print("  - 'evening' - Generate evening reflection")
    print("  - 'energy' - Check/record energy state")
    print("  - 'queue' - View surfacing queue")
    print("  - Or ask me anything about attention")
    print("\nType 'quit' to exit.\n")

    agent = create_curator_agent()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\nYour attention is precious. Use it well.")
                break

            # Handle quick commands
            if user_input.lower() == 'morning':
                user_input = "Generate a morning attention message for me. Keep it brief and actionable."

            if user_input.lower() == 'evening':
                user_input = "Generate an evening reflection prompt for me. Be warm - I'm probably tired."

            if user_input.lower() == 'energy':
                user_input = "Check my current energy state and ask me about how I'm feeling across the dimensions (physical, mental, emotional, social)."

            if user_input.lower() == 'queue':
                from ..tools.curator.attention import get_queue
                print(f"\n{get_queue()}\n")
                continue

            response = agent.process(user_input, ALL_HANDLERS)
            print(f"\nCurator: {response}\n")

        except KeyboardInterrupt:
            print("\n\nFarewell!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def morning_attention() -> str:
    """
    Generate morning attention content.

    Returns:
        Morning attention message
    """
    agent = create_curator_agent()
    prompt = load_prompt("curator", "morning")
    return agent.process(prompt, ALL_HANDLERS)


def evening_attention() -> str:
    """
    Generate evening reflection prompt.

    Returns:
        Evening reflection prompt
    """
    agent = create_curator_agent()
    prompt = load_prompt("curator", "evening")
    return agent.process(prompt, ALL_HANDLERS)


class AutonomousCuratorAgent(AutonomousAgent):
    """
    Autonomous Curator Agent that triggers at key moments.

    Checks:
    - Time: morning window (7-9am), evening window (8-10pm)
    - Proactive gaps: questions to ask the user
    - Actionable patterns: recurring intents that could become projects/tasks
    - Has morning/evening attention been delivered today?

    Work:
    - Generate morning attention
    - Generate evening reflection
    - Surface proactive questions (one at a time, with cooldowns)
    - Proactively create projects/tasks from detected patterns
    - Clean up old completed tasks

    Signals:
    - attention_delivered: After generating attention content
    """

    # Cooldown hours for each gap type
    GAP_COOLDOWNS = {
        "biographical.name": 168,      # 1 week
        "biographical.location": 168,  # 1 week
        "biographical.relationships": 336,  # 2 weeks
        "config.energy_baseline": 24,  # 1 day
    }

    # Proactive creation throttling
    PROACTIVE_CREATION_COOLDOWN = 24 * 60 * 60  # 24 hours between creations
    MAX_PROACTIVE_PER_WEEK = 3  # Maximum proactive items per week

    # Opportunity surfacing settings
    EXPIRING_SOON_DAYS = 7  # Surface time-sensitive opportunities expiring within this window
    MAX_EXPANSIVE_PER_WEEK = 2  # Limit expansive (surprise) opportunities to avoid overwhelm

    # Profile mining settings
    SEMANTIC_ANALYSIS_INTERVAL = 24 * 60 * 60  # Run semantic analysis once per day
    STALLED_PROJECT_DAYS = 14  # Projects with no activity for this long are considered stalled

    def __init__(self, morning_hour: int = 7, evening_hour: int = 21):
        super().__init__(
            name="curator",
            persona_name="curator",
            tools=ALL_TOOLS,
            tool_handlers=ALL_HANDLERS,
            check_interval=300,  # Check every 5 minutes
            signals_on_complete=["attention_delivered"]
        )
        self.morning_hour = morning_hour
        self.evening_hour = evening_hour

    def _load_surfaced_state(self) -> dict:
        """Load state tracking what's been surfaced to user."""
        surfaced_file = CURATOR_STATE_DIR / "surfaced.json"
        if surfaced_file.exists():
            try:
                return json.loads(surfaced_file.read_text())
            except:
                pass
        return {"questions_asked": {}, "capabilities_explained": [], "progress_shown_at": None}

    def _save_surfaced_state(self, surfaced: dict):
        """Save surfaced state."""
        surfaced_file = CURATOR_STATE_DIR / "surfaced.json"
        surfaced_file.write_text(json.dumps(surfaced, indent=2))

    def _get_gap_to_surface(self) -> dict | None:
        """
        Check gaps signal and find one to surface (respecting cooldowns).

        Returns:
            Gap dict to surface, or None if nothing should be surfaced.
        """
        gaps_file = SIGNALS_DIR / "proactive_gaps.json"
        if not gaps_file.exists():
            return None

        try:
            data = json.loads(gaps_file.read_text())
            gaps = data.get("gaps", [])
        except:
            return None

        if not gaps:
            return None

        surfaced = self._load_surfaced_state()
        questions_asked = surfaced.get("questions_asked", {})

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: priority_order.get(g.get("priority", "low"), 2))

        now = datetime.now()

        for gap in gaps:
            gap_id = gap.get("id")
            if not gap_id:
                continue

            # Check if this gap was recently surfaced
            asked_info = questions_asked.get(gap_id, {})
            last_asked = asked_info.get("last_asked")

            if last_asked:
                try:
                    last_asked_dt = datetime.fromisoformat(last_asked)
                    cooldown_hours = self.GAP_COOLDOWNS.get(gap_id, 72)  # Default 3 days
                    if now - last_asked_dt < timedelta(hours=cooldown_hours):
                        continue  # Still in cooldown
                except:
                    pass

            # This gap can be surfaced
            return gap

        return None

    def _mark_gap_surfaced(self, gap_id: str, answered: bool = False):
        """Mark a gap as having been surfaced."""
        surfaced = self._load_surfaced_state()
        questions_asked = surfaced.get("questions_asked", {})

        now = datetime.now().isoformat()
        if gap_id not in questions_asked:
            questions_asked[gap_id] = {
                "first_asked": now,
                "last_asked": now,
                "times_asked": 1,
                "answered": answered
            }
        else:
            questions_asked[gap_id]["last_asked"] = now
            questions_asked[gap_id]["times_asked"] = questions_asked[gap_id].get("times_asked", 0) + 1
            if answered:
                questions_asked[gap_id]["answered"] = True

        surfaced["questions_asked"] = questions_asked
        self._save_surfaced_state(surfaced)

    def _can_create_proactively(self) -> bool:
        """Check if proactive creation is allowed (respecting throttling)."""
        surfaced = self._load_surfaced_state()
        creations = surfaced.get("proactive_creations", [])

        now = datetime.now()

        # Check cooldown since last creation
        if creations:
            last_creation = datetime.fromisoformat(creations[-1].get("created_at", "2000-01-01"))
            if (now - last_creation).total_seconds() < self.PROACTIVE_CREATION_COOLDOWN:
                return False

        # Check weekly limit
        week_ago = now - timedelta(days=7)
        recent_creations = [
            c for c in creations
            if datetime.fromisoformat(c.get("created_at", "2000-01-01")) > week_ago
        ]
        if len(recent_creations) >= self.MAX_PROACTIVE_PER_WEEK:
            return False

        return True

    def _track_proactive_creation(self, item_type: str, title: str):
        """Track a proactive creation for throttling."""
        surfaced = self._load_surfaced_state()
        creations = surfaced.get("proactive_creations", [])

        creations.append({
            "created_at": datetime.now().isoformat(),
            "type": item_type,
            "title": title
        })

        # Keep only last 10 for cleanup
        surfaced["proactive_creations"] = creations[-10:]
        self._save_surfaced_state(surfaced)

    def _get_lifelog_hash(self) -> str:
        """Get hash of recent lifelog entries for cache validation."""
        # Hash recent log files (last 14 days would be in recent year dirs)
        import hashlib
        hasher = hashlib.md5()

        if LIFELOG_DIR.exists():
            # Get logs from last 14 days
            cutoff = datetime.now() - timedelta(days=14)
            for year_dir in sorted(LIFELOG_DIR.iterdir(), reverse=True):
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                for log_file in sorted(year_dir.glob("*.md")):
                    if log_file.name.startswith('_'):
                        continue
                    # Check if file is recent enough
                    try:
                        file_date = datetime.strptime(log_file.stem, "%Y-%m-%d")
                        if file_date.date() >= cutoff.date():
                            with open(log_file, 'rb') as f:
                                hasher.update(f.read())
                    except:
                        continue

        return hasher.hexdigest()

    def _load_patterns_cache(self) -> dict | None:
        """Load cached patterns if still valid."""
        if not PATTERNS_CACHE_FILE.exists():
            return None

        try:
            cache = json.loads(PATTERNS_CACHE_FILE.read_text())
            cached_hash = cache.get("lifelog_hash")
            current_hash = self._get_lifelog_hash()

            if cached_hash == current_hash:
                # Cache is valid
                return cache.get("patterns", [])
        except:
            pass

        return None

    def _save_patterns_cache(self, patterns: list):
        """Save patterns to cache with current lifelog hash."""
        cache = {
            "lifelog_hash": self._get_lifelog_hash(),
            "cached_at": datetime.now().isoformat(),
            "patterns": patterns
        }
        PATTERNS_CACHE_FILE.write_text(json.dumps(cache, indent=2))

    def _get_actionable_pattern(self) -> dict | None:
        """Get an actionable pattern to create proactively."""
        if not self._can_create_proactively():
            return None

        try:
            # Check cache first
            cached_patterns = self._load_patterns_cache()

            if cached_patterns is not None:
                self.logger.debug("Using cached actionable patterns")
                patterns = cached_patterns
            else:
                # Cache miss - detect patterns and cache result
                from ..tools.curator.context import detect_actionable_patterns
                patterns = detect_actionable_patterns(days=14, min_mentions=3)
                self._save_patterns_cache(patterns or [])
                self.logger.debug(f"Detected and cached {len(patterns or [])} patterns")

            if patterns:
                # Return the highest confidence pattern
                for pattern in patterns:
                    if pattern.get("confidence") in ("high", "medium"):
                        return pattern
        except Exception as e:
            self.logger.error(f"Error detecting actionable patterns: {e}")

        return None

    def _get_opportunity_to_surface(self) -> dict | None:
        """
        Check for opportunities needing attention.

        Surfaces:
        1. Time-sensitive opportunities expiring within EXPIRING_SOON_DAYS
        2. Expansive (surprise) opportunities when user has capacity

        Note: This is a stub - opportunity management was in the removed World agent.
        """
        # Opportunities feature was in the removed World agent
        # Return None for now - can be re-implemented if needed
        return None

    def _get_opportunity_to_surface_disabled(self) -> dict | None:
        """
        [DISABLED] Check for opportunities - was from World Agent.
        """
        try:
            # This import would fail since world was removed
            from ..tools.world.world import get_opportunities, OPPORTUNITIES_DIR
            import json

            surfaced = self._load_surfaced_state()
            expansive_surfaced = surfaced.get("expansive_surfaced_this_week", [])

            # Clean up old entries (older than 7 days)
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            expansive_surfaced = [
                e for e in expansive_surfaced
                if datetime.fromisoformat(e.get("date", "2000-01-01")) > week_ago
            ]
            surfaced["expansive_surfaced_this_week"] = expansive_surfaced
            self._save_surfaced_state(surfaced)

            # Check all opportunity categories
            for category in ["event", "person", "place", "learning", "goal", "other"]:
                cat_file = OPPORTUNITIES_DIR / f"{category}.json"
                if not cat_file.exists():
                    continue

                with open(cat_file, 'r') as f:
                    opportunities = json.load(f)

                for opp in opportunities:
                    # Skip already surfaced
                    if opp.get("surfaced"):
                        continue

                    opp_id = opp.get("id")

                    # Check for expiring time-sensitive opportunities
                    if opp.get("time_sensitive") and opp.get("expires"):
                        try:
                            expires_date = datetime.fromisoformat(opp["expires"].replace("Z", "+00:00"))
                            # Handle date-only strings
                            if expires_date.tzinfo is None and len(opp["expires"]) == 10:
                                expires_date = datetime.strptime(opp["expires"], "%Y-%m-%d")

                            days_until = (expires_date - now).days
                            if 0 < days_until <= self.EXPIRING_SOON_DAYS:
                                return {
                                    "type": "expiring",
                                    "opportunity": opp,
                                    "category": category,
                                    "days_until": days_until
                                }
                        except (ValueError, TypeError):
                            pass

                    # Check for expansive opportunities (if under weekly limit)
                    if opp.get("alignment") == "expansive":
                        if len(expansive_surfaced) < self.MAX_EXPANSIVE_PER_WEEK:
                            return {
                                "type": "expansive",
                                "opportunity": opp,
                                "category": category
                            }

        except Exception as e:
            self.logger.error(f"Error checking opportunities: {e}")

        return None

    def _surface_opportunity(self, opp_data: dict) -> str:
        """Surface an opportunity to the user via a task."""
        # This was from World agent which has been removed
        # Return early as this feature is disabled

        opp = opp_data.get("opportunity", {})
        opp_type = opp_data.get("type")
        category = opp_data.get("category", "opportunity")

        title = opp.get("title", "Opportunity")
        description = opp.get("description", "")
        url = opp.get("url", "")

        if opp_type == "expiring":
            days = opp_data.get("days_until", "?")
            task_title = f"⏰ Expiring soon: {title}"
            message = f"**{category.title()}** - Expires in {days} days\n\n{description[:300]}"
            priority = "high" if days <= 3 else "normal"
        else:  # expansive
            task_title = f"✨ Something different: {title}"
            message = f"**{category.title()}** - Outside your usual scope, but might be interesting\n\n{description[:300]}"
            priority = "low"

        if url:
            message += f"\n\nLink: {url}"

        create_euno_task(
            agent_name="curator",
            title=task_title,
            message=message,
            task_type="suggestion",
            priority=priority
        )

        # Mark as surfaced in World Agent data
        mark_opportunity_surfaced(opp.get("id", ""), "surfaced_by_attention")

        # Track expansive surfacing for weekly limit
        if opp_type == "expansive":
            surfaced = self._load_surfaced_state()
            expansive_list = surfaced.get("expansive_surfaced_this_week", [])
            expansive_list.append({
                "id": opp.get("id"),
                "date": datetime.now().isoformat()
            })
            surfaced["expansive_surfaced_this_week"] = expansive_list
            self._save_surfaced_state(surfaced)

        self.logger.info(f"Surfaced {opp_type} opportunity: {title}")
        return f"Surfaced opportunity: {title}"

    def _get_recent_lifelog_content(self, days: int = 7) -> str:
        """Get recent lifelog content for analysis."""
        content_parts = []
        now = datetime.now()

        for i in range(days):
            date = now - timedelta(days=i)
            year_dir = LIFELOG_DIR / str(date.year)
            log_file = year_dir / f"{date.strftime('%Y-%m-%d')}.md"

            if log_file.exists():
                try:
                    content_parts.append(f"## {date.strftime('%Y-%m-%d')}\n{log_file.read_text()}")
                except:
                    pass

        return "\n\n".join(content_parts) if content_parts else ""

    def _check_failure_mode_triggers(self) -> dict | None:
        """
        Check if recent lifelog entries match known behavioral patterns.

        Compares recent behavior against the profile to detect
        early warning signs and suggest interventions.
        """
        try:
            from ..tools.profiler.private_profile import get_profile_section

            # Get failure modes from profile
            failure_modes = get_profile_section("Failure Modes")
            if not failure_modes or failure_modes.startswith("Section"):
                return None

            # Get recent lifelog
            recent_logs = self._get_recent_lifelog_content(days=7)
            if not recent_logs:
                return None

            # Check cooldown - only run once per day
            surfaced = self._load_surfaced_state()
            last_check = surfaced.get("last_failure_mode_check")
            if last_check:
                last_check_dt = datetime.fromisoformat(last_check)
                if (datetime.now() - last_check_dt).total_seconds() < self.SEMANTIC_ANALYSIS_INTERVAL:
                    return None

            # Use the agent's LLM to analyze
            prompt = f"""Analyze whether recent lifelog entries show signs of the known failure modes.

## Known Failure Modes (from user profile)
{failure_modes}

## Recent Lifelog (last 7 days)
{recent_logs[:8000]}

## Task
1. Identify if any failure mode patterns are currently active or emerging
2. If a pattern is detected, suggest a specific, reversible intervention
3. Consider the user's epistemic style: prefer systems/environment design over willpower

Respond in JSON format:
{{
    "detected": true/false,
    "failure_mode": "which failure mode is triggered (if any)",
    "evidence": "specific quotes or patterns from the lifelog",
    "severity": "early_warning" | "active" | "crisis",
    "intervention": "specific, reversible suggestion aligned with their behavioral attractors"
}}

If no failure modes are detected, respond with {{"detected": false}}"""

            response = self.agent.process(prompt, {})

            # Parse response
            try:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    if result.get("detected"):
                        # Update last check time
                        surfaced["last_failure_mode_check"] = datetime.now().isoformat()
                        self._save_surfaced_state(surfaced)
                        return result
            except json.JSONDecodeError:
                pass

            # Update last check time even if nothing found
            surfaced["last_failure_mode_check"] = datetime.now().isoformat()
            self._save_surfaced_state(surfaced)

        except Exception as e:
            self.logger.error(f"Error checking failure modes: {e}")

        return None

    def _surface_failure_mode_intervention(self, analysis: dict) -> str:
        """Create an intervention task based on failure mode detection."""
        from ..tools.shared.profile_signals import emit_profile_observation

        failure_mode = analysis.get("failure_mode", "Unknown pattern")
        severity = analysis.get("severity", "early_warning")
        intervention = analysis.get("intervention", "Consider reviewing your current situation")
        evidence = analysis.get("evidence", "")

        # Set priority based on severity
        priority_map = {"early_warning": "low", "active": "normal", "crisis": "high"}
        priority = priority_map.get(severity, "normal")

        # Create intervention task
        title = f"🔔 Pattern noticed: {failure_mode[:50]}"
        message = f"**Detected**: {failure_mode}\n\n"
        if evidence:
            message += f"**Evidence**: {evidence[:200]}...\n\n"
        message += f"**Suggested action**: {intervention}"

        create_euno_task(
            agent_name="curator",
            title=title,
            message=message,
            task_type="intervention",
            priority=priority
        )

        # Emit observation for Synthesis Agent
        emit_profile_observation(
            agent="curator",
            signal_type="failure_mode_trigger",
            observation=f"Failure mode triggered: {failure_mode}",
            evidence=evidence[:500] if evidence else None,
            confidence="medium" if severity == "early_warning" else "high",
            suggested_section="Failure Modes",
            suggested_action="strengthen"
        )

        self.logger.info(f"Surfaced intervention for failure mode: {failure_mode}")
        return f"Intervention surfaced: {failure_mode}"

    def _check_stalled_projects(self) -> dict | None:
        """
        Check for projects that have stalled (no activity in STALLED_PROJECT_DAYS).

        Returns info about the most stalled project to nudge about.
        """
        try:
            from ..tools.worker.project import get_projects_data

            # Check cooldown
            surfaced = self._load_surfaced_state()
            last_check = surfaced.get("last_stalled_check")
            if last_check:
                last_check_dt = datetime.fromisoformat(last_check)
                # Only check once per day
                if (datetime.now() - last_check_dt).total_seconds() < self.SEMANTIC_ANALYSIS_INTERVAL:
                    return None

            # Get active projects
            projects = get_projects_data(status="active")
            if not projects:
                return None

            now = datetime.now()
            stalled_cutoff = now - timedelta(days=self.STALLED_PROJECT_DAYS)

            stalled_projects = []
            for project in projects:
                updated = project.get("updated")
                if updated:
                    try:
                        updated_dt = datetime.fromisoformat(updated)
                        if updated_dt < stalled_cutoff:
                            days_stalled = (now - updated_dt).days
                            stalled_projects.append({
                                "project": project,
                                "days_stalled": days_stalled
                            })
                    except:
                        pass

            # Update check time
            surfaced["last_stalled_check"] = datetime.now().isoformat()
            self._save_surfaced_state(surfaced)

            if stalled_projects:
                # Return the most stalled one
                stalled_projects.sort(key=lambda x: x["days_stalled"], reverse=True)
                return stalled_projects[0]

        except Exception as e:
            self.logger.error(f"Error checking stalled projects: {e}")

        return None

    def _surface_stalled_project(self, stalled_data: dict) -> str:
        """Create a nudge task for a stalled project."""
        project = stalled_data.get("project", {})
        days_stalled = stalled_data.get("days_stalled", 0)

        title = project.get("title", "Unknown project")
        project_id = project.get("id", "")

        task_title = f"📋 Stalled: {title}"
        message = f"This project hasn't had activity in **{days_stalled} days**.\n\n"
        message += "Consider:\n"
        message += "- Making one small step to restart momentum\n"
        message += "- Archiving if it's no longer relevant\n"
        message += "- Breaking it into smaller tasks"

        create_euno_task(
            agent_name="curator",
            title=task_title,
            message=message,
            task_type="nudge",
            priority="low"
        )

        self.logger.info(f"Surfaced stalled project nudge: {title}")
        return f"Stalled project nudged: {title}"

    def _run_semantic_analysis(self) -> dict | None:
        """
        Use LLM to semantically analyze recent lifelog for patterns.

        Detects:
        - Emotional patterns and stress buildup
        - Recurring frustrations
        - Implicit needs not yet articulated
        - Value-behavior divergence
        """
        try:
            from ..tools.profiler.private_profile import get_private_profile

            # Check cooldown
            surfaced = self._load_surfaced_state()
            last_analysis = surfaced.get("last_semantic_analysis")
            if last_analysis:
                last_dt = datetime.fromisoformat(last_analysis)
                if (datetime.now() - last_dt).total_seconds() < self.SEMANTIC_ANALYSIS_INTERVAL:
                    return None

            # Get profile and recent logs
            profile = get_private_profile()
            if not profile or profile.startswith("No private"):
                return None

            recent_logs = self._get_recent_lifelog_content(days=7)
            if not recent_logs or len(recent_logs) < 200:
                return None

            # Use agent's LLM for semantic analysis
            prompt = f"""Analyze recent lifelog entries for patterns the user might not have noticed.

## User's Identity Profile
{profile[:4000]}

## Recent Lifelog (last 7 days)
{recent_logs[:6000]}

## Task
Look for ONE of the following (pick the most significant):

1. **Emotional patterns**: Recurring moods, stress buildup, energy trends
2. **Recurring frustrations**: Things that keep coming up as problems
3. **Implicit needs**: Things the user seems to want but hasn't articulated
4. **Value-behavior gap**: Stated values vs actual behavior divergence

Respond in JSON format:
{{
    "pattern_type": "emotional" | "frustration" | "implicit_need" | "value_gap",
    "observation": "what you noticed (be specific, cite evidence)",
    "insight": "why this matters or what it might mean",
    "suggestion": "one gentle, reversible action they could consider",
    "confidence": "high" | "medium" | "low"
}}

Only respond if you find something genuinely useful. If nothing significant, respond: {{"pattern_type": null}}"""

            response = self.agent.process(prompt, {})

            # Parse response
            try:
                import re
                json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    if result.get("pattern_type"):
                        surfaced["last_semantic_analysis"] = datetime.now().isoformat()
                        self._save_surfaced_state(surfaced)
                        return result
            except json.JSONDecodeError:
                pass

            # Update time even if nothing found
            surfaced["last_semantic_analysis"] = datetime.now().isoformat()
            self._save_surfaced_state(surfaced)

        except Exception as e:
            self.logger.error(f"Error in semantic analysis: {e}")

        return None

    def _surface_semantic_insight(self, analysis: dict) -> str:
        """Create a task to surface a semantic insight."""
        pattern_type = analysis.get("pattern_type", "pattern")
        observation = analysis.get("observation", "")
        insight = analysis.get("insight", "")
        suggestion = analysis.get("suggestion", "")
        confidence = analysis.get("confidence", "medium")

        type_labels = {
            "emotional": "💭 Noticed",
            "frustration": "🔄 Recurring",
            "implicit_need": "💡 Might want",
            "value_gap": "⚖️ Consider"
        }
        label = type_labels.get(pattern_type, "💭 Noticed")

        title = f"{label}: {observation[:50]}..."
        message = f"**Observation**: {observation}\n\n"
        if insight:
            message += f"**Why it matters**: {insight}\n\n"
        if suggestion:
            message += f"**Consider**: {suggestion}"

        # Lower priority for lower confidence
        priority = "low" if confidence == "low" else "normal"

        create_euno_task(
            agent_name="curator",
            title=title,
            message=message,
            task_type="insight",
            priority=priority
        )

        self.logger.info(f"Surfaced semantic insight: {pattern_type}")
        return f"Insight surfaced: {pattern_type}"

    def _create_proactive_item(self, pattern: dict) -> str:
        """Create a project or task from a detected pattern and notify user."""
        item_type = pattern.get("type", "task")
        title = pattern.get("title", "Untitled")
        description = pattern.get("description", "")
        evidence = pattern.get("evidence", [])

        evidence_text = evidence[0] if evidence else ""

        try:
            if item_type == "project":
                from ..tools.worker.project import create_project
                result = create_project(
                    title=title,
                    description=f"Auto-created from pattern: {description}. Context: {evidence_text}",
                    project_type="goal",
                    source_agent="curator",
                    source_context=f"Detected recurring intent: {description}"
                )
            else:
                from ..tools.worker.task import create_task
                result = create_task(
                    description=title,
                    source_agent="curator",
                    source_context=f"Detected recurring intent: {description}"
                )

            # Track the creation
            self._track_proactive_creation(item_type, title)

            # Notify user via From Euno project task
            create_euno_task(
                agent_name="curator",
                title=f"Created: {title}",
                message=f"I noticed you've been thinking about this. {description}",
                task_type="notification",
                priority="normal"
            )

            self.logger.info(f"Proactively created {item_type}: {title}")
            return result

        except Exception as e:
            self.logger.error(f"Error creating proactive item: {e}")
            return f"Error creating {item_type}: {e}"

    def check_work_needed(self) -> bool:
        """Check if attention is needed based on time, signals, or proactive gaps."""
        now = datetime.now()
        today = now.date().isoformat()
        state = self.load_state()

        # Check for profile signal - profile has been updated
        if self.check_signal("profile_updated"):
            self.logger.info("Received profile_updated signal")
            state["profile_refreshed"] = True
            self.save_state(state)

        # Check morning window (7-9am)
        if self.morning_hour <= now.hour < self.morning_hour + 2:
            last_morning = state.get("last_morning_date")
            if last_morning != today:
                self.logger.info("Morning attention window - generating")
                state["pending_type"] = "morning"
                self.save_state(state)
                return True

        # Check evening window (9-11pm)
        if self.evening_hour <= now.hour < self.evening_hour + 2:
            last_evening = state.get("last_evening_date")
            if last_evening != today:
                self.logger.info("Evening attention window - generating")
                state["pending_type"] = "evening"
                self.save_state(state)
                return True

        # Check for proactive gaps to surface
        gap = self._get_gap_to_surface()
        if gap:
            self.logger.info(f"Found gap to surface: {gap.get('id')}")
            state["pending_type"] = "proactive"
            state["pending_gap"] = gap
            self.save_state(state)
            return True

        # Check for actionable patterns to create proactively
        pattern = self._get_actionable_pattern()
        if pattern:
            self.logger.info(f"Found actionable pattern: {pattern.get('title')}")
            state["pending_type"] = "proactive_create"
            state["pending_pattern"] = pattern
            self.save_state(state)
            return True

        # Check for opportunities needing attention (expiring or expansive)
        opportunity = self._get_opportunity_to_surface()
        if opportunity:
            opp_type = opportunity.get("type", "unknown")
            opp_title = opportunity.get("opportunity", {}).get("title", "unknown")
            self.logger.info(f"Found {opp_type} opportunity to surface: {opp_title}")
            state["pending_type"] = "opportunity"
            state["pending_opportunity"] = opportunity
            self.save_state(state)
            return True

        # Check for failure mode triggers (profile mining)
        failure_mode = self._check_failure_mode_triggers()
        if failure_mode:
            self.logger.info(f"Detected failure mode: {failure_mode.get('failure_mode')}")
            state["pending_type"] = "failure_mode"
            state["pending_failure_mode"] = failure_mode
            self.save_state(state)
            return True

        # Check for stalled projects
        stalled = self._check_stalled_projects()
        if stalled:
            self.logger.info(f"Found stalled project: {stalled.get('project', {}).get('title')}")
            state["pending_type"] = "stalled_project"
            state["pending_stalled"] = stalled
            self.save_state(state)
            return True

        # Run semantic analysis for patterns
        semantic = self._run_semantic_analysis()
        if semantic:
            self.logger.info(f"Detected semantic pattern: {semantic.get('pattern_type')}")
            state["pending_type"] = "semantic_insight"
            state["pending_semantic"] = semantic
            self.save_state(state)
            return True

        # Check if cleanup is needed (once per day during evening window)
        if self.evening_hour <= now.hour < self.evening_hour + 2:
            last_cleanup = state.get("last_task_cleanup")
            if last_cleanup != today:
                self.logger.info("Task cleanup needed")
                state["pending_type"] = "cleanup"
                self.save_state(state)
                return True

        return False

    def do_work(self) -> str:
        """Generate morning/evening attention, surface proactive question, or create items."""
        state = self.load_state()
        pending_type = state.get("pending_type", "morning")
        today = datetime.now().date().isoformat()

        if pending_type == "proactive":
            # Surface a proactive question via From Euno project task
            gap = state.get("pending_gap")
            if gap:
                create_euno_task(
                    agent_name="curator",
                    title=gap.get("question", "Quick question"),
                    message=gap.get("context", ""),
                    task_type="question",
                    priority="normal"
                )
                self._mark_gap_surfaced(gap.get("id"))
                self.logger.info(f"Surfaced proactive question: {gap.get('id')}")

            # Clear flags
            state["pending_type"] = None
            state["pending_gap"] = None
            self.save_state(state)
            return "Proactive question surfaced"

        elif pending_type == "proactive_create":
            # Create a project or task from detected pattern
            pattern = state.get("pending_pattern")
            result = "No pattern found"
            if pattern:
                result = self._create_proactive_item(pattern)

            # Clear flags
            state["pending_type"] = None
            state["pending_pattern"] = None
            self.save_state(state)
            return result

        elif pending_type == "opportunity":
            # Surface an opportunity (expiring or expansive)
            opp_data = state.get("pending_opportunity")
            result = "No opportunity found"
            if opp_data:
                result = self._surface_opportunity(opp_data)

            # Clear flags
            state["pending_type"] = None
            state["pending_opportunity"] = None
            self.save_state(state)
            return result

        elif pending_type == "failure_mode":
            # Surface a failure mode intervention
            failure_data = state.get("pending_failure_mode")
            result = "No failure mode data"
            if failure_data:
                result = self._surface_failure_mode_intervention(failure_data)

            # Clear flags
            state["pending_type"] = None
            state["pending_failure_mode"] = None
            self.save_state(state)
            return result

        elif pending_type == "stalled_project":
            # Surface a stalled project nudge
            stalled_data = state.get("pending_stalled")
            result = "No stalled project data"
            if stalled_data:
                result = self._surface_stalled_project(stalled_data)

            # Clear flags
            state["pending_type"] = None
            state["pending_stalled"] = None
            self.save_state(state)
            return result

        elif pending_type == "semantic_insight":
            # Surface a semantic pattern insight
            semantic_data = state.get("pending_semantic")
            result = "No semantic data"
            if semantic_data:
                result = self._surface_semantic_insight(semantic_data)

            # Clear flags
            state["pending_type"] = None
            state["pending_semantic"] = None
            self.save_state(state)
            return result

        elif pending_type == "cleanup":
            # Clean up old completed tasks
            from ..tools.worker.task import cleanup_old_completed_tasks
            result = cleanup_old_completed_tasks(retention_days=30)
            state["last_task_cleanup"] = today
            state["pending_type"] = None
            self.save_state(state)
            self.logger.info(f"Task cleanup completed: {result}")
            return result

        elif pending_type == "morning":
            result = morning_attention()
            state["last_morning_date"] = today
            state["last_morning_content"] = result
            self.logger.info("Morning attention generated")

            # Send notification via From Euno project task
            create_euno_task(
                agent_name="curator",
                title="Good morning",
                message=result,
                task_type="notification",
                priority="normal"
            )
        else:
            result = evening_attention()
            state["last_evening_date"] = today
            state["last_evening_content"] = result
            self.logger.info("Evening attention generated")

            # Send notification via From Euno project task
            create_euno_task(
                agent_name="curator",
                title="Evening reflection",
                message=result,
                task_type="notification",
                priority="normal"
            )

        # Clear flags
        state["pending_type"] = None
        state["new_opportunities"] = False
        self.save_state(state)

        self.agent.clear_context()
        return f"{pending_type.title()} attention delivered"

    def get_latest_attention(self) -> dict:
        """Get the most recent attention content for display."""
        state = self.load_state()
        return {
            "morning": state.get("last_morning_content"),
            "morning_date": state.get("last_morning_date"),
            "evening": state.get("last_evening_content"),
            "evening_date": state.get("last_evening_date")
        }


if __name__ == "__main__":
    run_interactive()
