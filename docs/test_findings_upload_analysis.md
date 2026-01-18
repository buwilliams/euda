# Upload Analysis Test Findings

**Test Date:** 2026-01-18
**Test Subject:** Lifelog content upload and identity extraction
**Status:** Ready for implementation

---

## Quick Start for Future Sessions

**Task:** Implement document analysis at upload time so users see immediate value from uploaded content.

**To understand the problem:**
```bash
# Upload a test file
curl -X POST http://localhost:8000/api/upload -F "file=@lifelog/Biography.txt"

# Check what was stored - note it's just "Uploaded Biography.txt" with type "thing"
python main.py dev memory user

# Check profile - still empty, no extraction happened
python main.py dev profile user
```

**Key insight:** Uploads are stored but never analyzed. The system doesn't understand what the document *means* for the user's identity.

---

## Project Context

### What is Euno?

Euno is a personal intelligence that learns to anticipate you. Key vision points from `docs/1_pitch.md`:

- "Build a real model of the user" - The system should understand who you are
- "Users see advantages quickly" - Value should be immediate, not delayed
- "Anticipate based on who you are" - Requires populated profile and semantic memories

### The User Agent

The user is conceptually an agent with:
- **Profile** (`data/agents/user/identity.md`): Identity, interests, biographical info
- **Short-term memory** (`data/agents/user/memory/short-term.jsonl`): Active items (goals, concerns, people, etc.)
- **Long-term memory** (`data/agents/user/memory/long-term/{year}/{date}.md`): Permanent archive

### Memory Types

From `src/tools/data/memory.py`, valid memory types are:
```python
MEMORY_TYPES = ["person", "place", "thing", "goal", "concern", "idea", "learning", "behavior"]
```

Currently, ALL uploads become type "thing" regardless of content.

---

## Architecture Overview

### Upload Flow (Current)

```
User uploads file
       ↓
src/web/routes/upload.py
       ↓
1. Save to data/agents/user/uploads/{date}/{filename}
2. If text < 100KB: dump raw content to long-term memory
3. Add generic short-term entry: "Uploaded {filename}" (type: thing)
       ↓
Done - NO ANALYSIS
```

### Reflection Flow (Consolidation)

```
Trigger: time:evening (or manual via dev CLI)
       ↓
src/reflection/consolidate.py
       ↓
1. Load short-term memory
2. Load recent long-term memory
3. Call LLM with consolidate prompt
4. Graduate memories, update profile
       ↓
Profile updated (but focuses on behavioral patterns, not document content)
```

### Relevant Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `src/web/routes/upload.py` | Upload endpoint | `upload_file()` - where to add analysis |
| `src/tools/data/memory.py` | Memory CRUD | `add_memory()`, `write_long_term_memory()` |
| `src/reflection/consolidate.py` | Daily consolidation | `run_consolidate()` |
| `src/reflection/prompts.py` | Builds LLM prompts | `build_consolidate_prompt()` |
| `data/system/prompts/reflection/consolidate_system_user.md` | Consolidate system prompt | Needs document extraction instructions |
| `data/agents/user/identity.md` | User profile | Target for extracted identity |
| `src/llm.py` | LLM client | `call_llm()` for analysis calls |

---

## Current Implementation Details

### Upload Endpoint (`src/web/routes/upload.py`)

```python
@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for processing."""
    today = datetime.now().strftime("%Y-%m-%d")
    upload_dir = get_upload_dir()

    # Save file
    filename = make_unique_filename(upload_dir, file.filename)
    file_path = upload_dir / filename
    content_bytes = await file.read()
    file_path.write_bytes(content_bytes)

    # For text files, add content to long-term memory
    if is_text and file_size <= MAX_TEXT_SIZE:
        text_content = content_bytes.decode("utf-8")
        memory_content = f"**Uploaded file:** {filename}\n\n```\n{text_content}\n```"
        write_long_term_memory(
            content=memory_content,  # RAW DUMP - no analysis
            agent_id="user",
            source="Upload"
        )

    # Add brief entry to short-term memory
    add_memory(
        short_description=f"Uploaded {filename}",  # GENERIC - no extraction
        type="thing",  # ALWAYS "thing" - no classification
        agent_id="user"
    )

    return {"status": "uploaded", ...}
```

### Memory Functions (`src/tools/data/memory.py`)

```python
def add_memory(
    short_description: str,
    type: str,  # Must be one of MEMORY_TYPES
    agent_id: str = "user",
    date_mentioned: str = None,
    date_expected: str = None
) -> dict:
    """Add an item to short-term memory."""
    # Creates entry in data/agents/{agent_id}/memory/short-term.jsonl

def write_long_term_memory(
    content: str,
    agent_id: str = "user",
    source: str = "System"
) -> dict:
    """Write an entry to long-term memory."""
    # Appends to data/agents/{agent_id}/memory/long-term/{year}/{date}.md
```

### LLM Client (`src/llm.py`)

```python
def call_llm(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    tools: list = None,
    response_format: dict = None  # For JSON mode
) -> dict:
    """Call the LLM API."""
    # Returns: {"content": "...", "tool_calls": [...], ...}
```

---

## Test Results

### Phase 1: Baseline State

| Metric | Value |
|--------|-------|
| Short-term memory items | 7 |
| Profile state | Empty template |
| Long-term memory files | 3 older files (Jan 9-11) |

### Phase 2: Upload Processing

**Uploaded:** 11 lifelog files (Biography, LinkedIn Profile, Routine, philosophical essays)

| File | Size | Processing |
|------|------|------------|
| A Primer on Logic.txt | 15.9KB | Raw dump to long-term |
| AI Economics - The Time Traveler's Gift.txt | 3.5KB | Raw dump to long-term |
| Biography.txt | 2.7KB | Raw dump to long-term |
| Cyclic Rationality.txt | 8.5KB | Raw dump to long-term |
| Economics in the Intelligence Age.txt | 13.1KB | Raw dump to long-term |
| LinkedIn Profile.txt | 17.7KB | Raw dump to long-term |
| Routine.txt | 1.8KB | Raw dump to long-term |
| Technohumanism.txt | 16.7KB | Raw dump to long-term |
| The Rise of the Outcome Economy.txt | 16.1KB | Raw dump to long-term |
| Utility of Truth.txt | 6.3KB | Raw dump to long-term |
| Why Hypotheticals Matter.txt | 8.0KB | Raw dump to long-term |

**Result after upload:**
- Short-term memory: 18 items (7 original + 11 uploads)
- All 11 uploads are type "thing" with description "Uploaded {filename}"
- Profile: Still empty (no extraction)
- Long-term memory: 1,423 lines of raw content

### Phase 3: Storage Verification

**Short-term memory entries for uploads:**
```
mem-493e2703 [thing] Uploaded A Primer on Logic.txt
mem-f33e755b [thing] Uploaded AI Economics - The Time Traveler's Gift.txt
mem-29e4bcdd [thing] Uploaded Biography.txt
...all type "thing", all generic descriptions
```

**Gap identified:** All uploads become generic "thing" type entries. The system does not:
- Classify documents by type (biography, essay, professional profile)
- Extract goals, interests, concerns, or biographical facts
- Create semantic memory entries (person, goal, interest, etc.)

### Phase 4: Consolidation Results

After running `python main.py dev reflect user --consolidate`:

**Profile update received:**
```
## Reflection Update (2026-01-18)

Voice: prefers concise, practical guidance optimized for action...
Interests: rationality/logic, AI economics/future of work, technohumanism...
Biographical Information: user identity noted as Emma; family includes teens and son Isaac.
```

**Gaps identified:**
1. Biographical info is **wrong** - says "Emma" but uploaded Biography.txt shows "Buddy Williams"
2. Interests extracted are **from previous short-term memory**, not uploaded documents
3. Uploaded documents not specifically parsed - consolidation focuses on "behavioral patterns from actions"

### Phase 5: Conversation Context

**Test 1:** Default agent (assistant) - no context
```
Q: "What do you know about me?"
A: "I only know what you've told me in this chat."
```

**Test 2:** Chat agent with explicit prompt - context available
```
Q: "What do you know about me? Check my profile and memory."
A: Retrieved profile and memory successfully (but with incorrect data)
```

---

## Identified Gaps

### Gap 1: No LLM Analysis at Upload Time

**Location:** `src/web/routes/upload.py:69-136`

**Current behavior:**
1. File saved to `data/agents/user/uploads/{date}/`
2. Text files < 100KB: Raw content wrapped in markdown code block dumped to long-term memory
3. Generic short-term entry: `"Uploaded {filename}"` (type: thing)

**What's missing:**
- No LLM call to extract identity elements
- No document classification
- No semantic memory creation (goals, interests, biographical facts)

### Gap 2: Generic Memory Type for All Uploads

**Location:** `src/web/routes/upload.py:124-128`

```python
add_memory(
    short_description=f"Uploaded {filename}",
    type="thing",  # Always "thing" - no classification
    agent_id="user"
)
```

**What's needed:**
- Document-aware memory types (biography → person facts, essays → interests/ideas)
- Content-based classification

### Gap 3: Consolidation Prompt Mismatch

**Location:** `data/system/prompts/reflection/consolidate_system_user.md`

**Current focus:**
- "Analyze behavioral patterns"
- "What their actions reveal"
- "Learning and behavior items"

**What's missing:**
- No instruction to parse uploaded documents
- No document analysis phase
- No biographical extraction from uploaded content

### Gap 4: Memory Not Auto-Injected to Chat

**Location:** `src/agent.py:246-247`

```python
# Note: Memory is NOT auto-injected.
# Agents should use list_memory and read_long_term_memory tools when needed.
```

**Impact:**
- Users must explicitly ask agent to check profile/memory
- Default behavior suggests agent doesn't know the user

---

## Implementation Plan

### Recommended: Option C (Hybrid Approach)

Implement both immediate analysis (at upload) AND enhanced consolidation (daily synthesis).

### Step 1: Add Document Analysis Function

**File:** `src/web/routes/upload.py`

Add after imports:
```python
from ...llm import call_llm
import json

ANALYSIS_PROMPT = """Analyze this uploaded document and extract identity-relevant information.

Document filename: {filename}
Document content:
{content}

Return a JSON object with:
{{
  "document_type": "biography|essay|professional_profile|routine|journal|notes|other",
  "summary": "1-2 sentence summary of what this document is",
  "biographical_facts": ["fact1", "fact2", ...],  // Name, family, location, etc.
  "interests": ["interest1", "interest2", ...],   // Topics, hobbies, intellectual interests
  "goals": ["goal1", "goal2", ...],               // Aspirations, objectives mentioned
  "concerns": ["concern1", ...],                  // Worries, fears, challenges
  "key_insights": ["insight1", "insight2", ...]   // 3-5 most important takeaways
}}

Only include fields where you find relevant information. Be concise."""


async def analyze_document(filename: str, content: str) -> dict | None:
    """Analyze uploaded document for identity extraction.

    Returns dict with extracted info, or None if analysis fails.
    Cost: ~$0.01-0.03 per document depending on size.
    """
    # Truncate very long content
    max_content = 50000
    if len(content) > max_content:
        content = content[:max_content] + "\n\n[Content truncated for analysis]"

    try:
        response = call_llm(
            messages=[{
                "role": "user",
                "content": ANALYSIS_PROMPT.format(filename=filename, content=content)
            }],
            model="gpt-4o-mini",  # Fast and cheap
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        return json.loads(response.get("content", "{}"))
    except Exception as e:
        print(f"[Upload] Document analysis failed: {e}")
        return None
```

### Step 2: Modify Upload Endpoint

**File:** `src/web/routes/upload.py`

Replace the current `upload_file` function:
```python
@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for processing.

    Saves the file and analyzes it for identity extraction:
    - Text files: analyzed by LLM for biographical facts, interests, goals
    - All files: brief entry added to short-term memory
    """
    today = datetime.now().strftime("%Y-%m-%d")
    upload_dir = get_upload_dir()

    # Save file with unique name if needed
    filename = make_unique_filename(upload_dir, file.filename)
    file_path = upload_dir / filename
    content_bytes = await file.read()
    file_path.write_bytes(content_bytes)

    # Determine file type and size
    file_size = len(content_bytes)
    file_size_str = f"{file_size / 1024:.1f}KB" if file_size >= 1024 else f"{file_size}B"
    is_text = is_text_file(filename)

    analysis = None
    memories_created = []

    # For text files, analyze and add to memory
    if is_text and file_size <= MAX_TEXT_SIZE:
        try:
            text_content = content_bytes.decode("utf-8")

            # NEW: Analyze document for identity extraction
            analysis = await analyze_document(filename, text_content)

            # Store raw content in long-term memory (unchanged)
            memory_content = f"**Uploaded file:** {filename}\n\n```\n{text_content}\n```"
            write_long_term_memory(
                content=memory_content,
                agent_id="user",
                source="Upload"
            )

            # NEW: Create semantic memories from analysis
            if analysis:
                # Add interests as memories
                for interest in analysis.get("interests", [])[:3]:
                    add_memory(
                        short_description=f"Interest: {interest}",
                        type="idea",
                        agent_id="user"
                    )
                    memories_created.append(f"[idea] {interest}")

                # Add goals as memories
                for goal in analysis.get("goals", [])[:2]:
                    add_memory(
                        short_description=goal,
                        type="goal",
                        agent_id="user"
                    )
                    memories_created.append(f"[goal] {goal}")

                # Add concerns as memories
                for concern in analysis.get("concerns", [])[:2]:
                    add_memory(
                        short_description=concern,
                        type="concern",
                        agent_id="user"
                    )
                    memories_created.append(f"[concern] {concern}")

                # Store analysis summary in long-term memory
                if analysis.get("key_insights"):
                    insights_content = f"**Document analysis:** {filename}\n\n"
                    insights_content += f"Type: {analysis.get('document_type', 'unknown')}\n"
                    insights_content += f"Summary: {analysis.get('summary', 'N/A')}\n\n"
                    insights_content += "Key insights:\n"
                    for insight in analysis.get("key_insights", []):
                        insights_content += f"- {insight}\n"

                    write_long_term_memory(
                        content=insights_content,
                        agent_id="user",
                        source="Upload Analysis"
                    )

        except UnicodeDecodeError:
            # Not actually text
            write_long_term_memory(
                content=f"**Uploaded file:** {filename} ({file_size_str}) - binary file",
                agent_id="user",
                source="Upload"
            )
    else:
        # Binary or large file
        write_long_term_memory(
            content=f"**Uploaded file:** {filename} ({file_size_str})",
            agent_id="user",
            source="Upload"
        )

    # Add main upload entry to short-term memory (with better description if analyzed)
    if analysis:
        doc_type = analysis.get("document_type", "document")
        summary = analysis.get("summary", f"Uploaded {filename}")
        add_memory(
            short_description=f"Uploaded {doc_type}: {summary[:100]}",
            type="thing",
            agent_id="user"
        )
    else:
        add_memory(
            short_description=f"Uploaded {filename}",
            type="thing",
            agent_id="user"
        )

    return {
        "status": "uploaded",
        "filename": filename,
        "path": f"uploads/{today}/{filename}",
        "size": file_size_str,
        "analyzed": analysis is not None,
        "memories_created": memories_created,
        "message": "File saved and analyzed." if analysis else "File saved."
    }
```

### Step 3: Enhance Consolidation Prompt

**File:** `data/system/prompts/reflection/consolidate_system_user.md`

Add this section before "## Output Format":
```markdown
## Document Analysis

When analyzing long-term memory, pay special attention to uploaded documents.

For documents that appear to be:
- **Biography/Resume**: Extract name, family, career history, education → update Biographical Information
- **Professional Profile**: Extract skills, achievements, career goals → update Interests and Biographical Information
- **Routine/Schedule**: Extract habits, preferences, daily patterns → update Behavioral Rules
- **Essays/Writing**: Extract intellectual interests, worldview, values → update Interests and Stable Attractors
- **Journal/Notes**: Extract current concerns, goals, emotional state → use for Wants and Fears

Cross-reference uploaded content with existing profile to:
1. Correct any inconsistencies (prefer explicit document content over inferred data)
2. Fill in missing sections with documented facts
3. Identify patterns across multiple documents
```

### Step 4: Add Test Coverage

**File:** Create `tests/test_upload_analysis.py`

```python
"""Tests for upload document analysis."""

import pytest
from pathlib import Path

# Test that biography extraction works
def test_biography_extraction():
    """Verify biography documents extract biographical facts."""
    # Upload Biography.txt
    # Check short-term memory for proper types (not just "thing")
    # Check profile was updated with name, family info
    pass

# Test that essays extract interests
def test_essay_interest_extraction():
    """Verify essay documents extract interests."""
    # Upload an essay file
    # Check short-term memory for "idea" type entries
    pass

# Test that routine extracts behavioral info
def test_routine_extraction():
    """Verify routine documents extract behavioral patterns."""
    # Upload Routine.txt
    # Check for behavioral patterns in memory
    pass
```

---

## Verification Commands

After implementation, run these to verify:

```bash
# 1. Start fresh (optional - backup first)
# rm -rf data/agents/user/memory/short-term.jsonl

# 2. Start server
python main.py start &

# 3. Upload a test file
curl -X POST http://localhost:8000/api/upload \
  -F "file=@lifelog/Biography.txt"

# 4. Check the response - should show analyzed: true and memories_created
# Expected: memories_created: ["[idea] ...", "[goal] ...", etc.]

# 5. Check short-term memory - should have semantic types, not just "thing"
python main.py dev memory user
# Expected: [goal], [idea], [concern] entries, not just [thing]

# 6. Check profile after consolidation
python main.py dev reflect user --consolidate
python main.py dev profile user
# Expected: Biographical Information should have correct name from Biography.txt

# 7. Test chat context
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my interests?", "agent_id": "chat"}'
# Expected: Agent should reference extracted interests
```

---

## Cost Estimate

| Operation | Model | Est. Cost |
|-----------|-------|-----------|
| Document analysis (per file) | gpt-4o-mini | $0.01-0.03 |
| 11 lifelog files | gpt-4o-mini | ~$0.15-0.30 |
| Daily consolidation | gpt-4o | ~$0.10-0.20 |

Total for initial lifelog upload: ~$0.25-0.50

---

## Success Criteria

After implementation:

| Metric | Before | After |
|--------|--------|-------|
| Time to see value from upload | Hours (daily consolidation) | Seconds |
| Memory type for uploads | Always "thing" | Semantic (goal, idea, concern) |
| Profile after Biography.txt upload | Empty | Has name, family info |
| Chat can answer "What are my interests?" | No (requires explicit prompt) | Yes (semantic memories exist) |

---

## Related Documentation

- `docs/1_pitch.md` - Product vision (why this matters)
- `docs/3_agents.md` - Agent architecture
- `spec/2_data.md` - Data structures and schemas
- `CLAUDE.md` - Development setup and testing

---

## Conclusion

The upload system stores files but doesn't extract value. This implementation adds:

1. **Immediate analysis** - LLM extracts identity elements at upload time
2. **Semantic memories** - Proper types (goal, idea, concern) instead of generic "thing"
3. **Enhanced consolidation** - Document-aware synthesis for profile updates

**Core principle:** Documents should be understood, not just stored.
