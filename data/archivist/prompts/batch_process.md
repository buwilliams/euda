# Batch Process Prompt

*Instructions for processing multiple files and creating log entries*

Process these {file_count} files and return log entries as JSON.

For EACH file, determine:

1. **Content type:**
   - PRESERVE VERBATIM (human expression): journals, musings, reflections, notes, messages, emails, conversations, quotes, ideas, blog posts
     → Record the actual words. Voice and expression matter.
   - SUMMARIZE (data/information): transactions, receipts, articles, reports, lists, logs
     → Compress to essence. 2-5 sentences max.

2. **Appropriate entry_type:**
   - "journal" / "reflection" / "thought" for personal writing
   - "message" / "conversation" / "email" for communications
   - "summary" for compressed data

3. **Timestamp:** Use temporal hint if available, otherwise extract from content or leave null

Return ONLY valid JSON in this exact format (no other text):
```json
{
  "entries": [
    {
      "file_name": "example.txt",
      "content": "The log entry content...",
      "timestamp": "2024-12-24T10:00:00",
      "source": "text_file",
      "entry_type": "journal",
      "temporal_confidence": "high",
      "temporal_source": "filename"
    }
  ]
}
```

## Field Definitions

| Field | Required | Description |
|-------|----------|-------------|
| file_name | Yes | Original filename (for tracking) |
| content | Yes | The log entry content (verbatim or summarized) |
| timestamp | No | ISO timestamp if determinable, null otherwise |
| source | Yes | Data source type (e.g., "text_file", "image", "pdf") |
| entry_type | Yes | Type of entry (journal, message, summary, etc.) |
| temporal_confidence | Yes | "high", "medium", or "low" |
| temporal_source | Yes | How timestamp was determined |

## Entry Types

**Verbatim types** (no length limit):
- journal, reflection, thought, musing, note
- message, conversation, email, text, letter
- quote, idea, blog, writing

**Summary types** (max 7 sentences):
- summary, receipt, transaction, report

## FILES TO PROCESS

{files_content}
