# Process File Prompt

*Instructions for processing a file and creating a log entry*

## Context

File: {file_name}
Category: {category}
{temporal_note}

## Content

---
{content}
---

## Task

CRITICAL: First determine what kind of content this is:

**PRESERVE VERBATIM** (human expression):
- Personal writing: journals, musings, reflections, notes, blog posts
- Messages from others: texts, emails, letters, conversations
- Quotes, ideas, thoughts - yours or others'
→ Record the actual words. Voice and expression matter.

**SUMMARIZE** (data/information):
- Transactions, receipts, financial records
- Articles, reports, documentation
- Lists, logs, system output
→ Compress to essence. 2-5 sentences max.

## Instructions

1. Determine: Is this human expression or data/information?
2. If human expression → preserve the actual words, the voice, the meaning
3. If data/information → summarize briefly (what happened, key numbers, significance)
4. Use write_log_entry with appropriate entry_type:
   - "journal" / "reflection" / "thought" for personal writing
   - "message" / "conversation" for communications
   - "summary" for compressed data
5. Use the temporal hint for timestamp if available

The goal: Capture real thoughts and words verbatim. Compress everything else.

Do NOT read the file again - use the content provided above.
