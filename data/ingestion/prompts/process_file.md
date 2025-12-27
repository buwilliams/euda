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
4. **DETERMINE THE CORRECT TIMESTAMP:**
   - If temporal hint is provided with high confidence → use it
   - If content mentions dates (e.g., "January 15, 2016", "2016-01-15") → extract and use that date
   - If low confidence hint (file_mtime) but content clearly from another time → use content date
   - The timestamp should be when the content was CREATED, not when uploaded
5. Use write_log_entry with:
   - **timestamp**: The determined date (REQUIRED for historical content)
   - **entry_type**: "journal"/"reflection"/"thought" for personal writing, "message"/"conversation" for communications, "summary" for compressed data
   - **temporal_confidence**: "high" if from content/filename, "medium" if inferred, "low" if uncertain
   - **temporal_source**: How you determined the date (e.g., "content", "filename", "temporal_hint")

**IMPORTANT**: Historical content must be stored with its original date, not today's date.
If the content is clearly from 2016, the timestamp MUST be a 2016 date.

The goal: Capture real thoughts and words verbatim. Compress everything else.

Do NOT read the file again - use the content provided above.
