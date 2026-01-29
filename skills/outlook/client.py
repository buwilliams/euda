"""Microsoft Graph API wrapper for Outlook skill."""

from datetime import datetime, timedelta
from typing import Optional

import requests

from skills.outlook.auth import get_access_token
from skills.outlook.storage import resolve_account

GRAPH_URL = "https://graph.microsoft.com/v1.0"


def graph_request(
    method: str,
    endpoint: str,
    account_name: Optional[str] = None,
    params: Optional[dict] = None,
    json_data: Optional[dict] = None,
) -> dict:
    """Make an authenticated request to Microsoft Graph API.

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE)
        endpoint: API endpoint (e.g., '/me/messages')
        account_name: Account to use (uses default if not specified)
        params: Query parameters
        json_data: JSON body for POST/PATCH requests

    Returns:
        Dict with API response or {'error': 'message'}
    """
    account = resolve_account(account_name)
    if not account:
        return {"error": "No account configured. Add one with: euno skills outlook accounts add <name>"}

    token = get_access_token(account)
    if not token:
        return {"error": f"Not authenticated for account '{account}'. Re-authenticate with: euno skills outlook accounts add {account}"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    url = f"{GRAPH_URL}{endpoint}"

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_data,
            timeout=30,
        )

        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except Exception:
                error_msg = response.text
            return {"error": f"API error ({response.status_code}): {error_msg}"}

        if response.content:
            return response.json()
        return {}

    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"error": "Could not connect to Microsoft Graph API"}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Mail Functions
# =============================================================================


def list_messages(
    account_name: Optional[str] = None,
    limit: int = 10,
    unread_only: bool = False,
    folder: str = "inbox",
) -> dict:
    """List email messages.

    Args:
        account_name: Account to use
        limit: Maximum number of messages to return
        unread_only: Only return unread messages
        folder: Mail folder (inbox, drafts, sentitems, deleteditems, etc.)

    Returns:
        Dict with messages list or error
    """
    params = {
        "$top": limit,
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview,hasAttachments",
    }

    if unread_only:
        params["$filter"] = "isRead eq false"

    result = graph_request("GET", f"/me/mailFolders/{folder}/messages", account_name, params=params)

    if "error" in result:
        return result

    messages = []
    for m in result.get("value", []):
        from_addr = m.get("from", {}).get("emailAddress", {})
        messages.append({
            "id": m["id"],
            "subject": m.get("subject", "(No subject)"),
            "from_name": from_addr.get("name", ""),
            "from_email": from_addr.get("address", ""),
            "received": m.get("receivedDateTime"),
            "is_read": m.get("isRead", False),
            "has_attachments": m.get("hasAttachments", False),
            "preview": m.get("bodyPreview", "")[:150],
        })

    return {
        "account": resolve_account(account_name),
        "folder": folder,
        "count": len(messages),
        "messages": messages,
    }


def get_message(message_id: str, account_name: Optional[str] = None) -> dict:
    """Get a single email message with full body.

    Args:
        message_id: Message ID
        account_name: Account to use

    Returns:
        Dict with message details or error
    """
    result = graph_request("GET", f"/me/messages/{message_id}", account_name)

    if "error" in result:
        return result

    from_addr = result.get("from", {}).get("emailAddress", {})
    to_addrs = [r.get("emailAddress", {}).get("address", "") for r in result.get("toRecipients", [])]
    cc_addrs = [r.get("emailAddress", {}).get("address", "") for r in result.get("ccRecipients", [])]

    return {
        "account": resolve_account(account_name),
        "id": result["id"],
        "subject": result.get("subject", "(No subject)"),
        "from_name": from_addr.get("name", ""),
        "from_email": from_addr.get("address", ""),
        "to": to_addrs,
        "cc": cc_addrs,
        "received": result.get("receivedDateTime"),
        "is_read": result.get("isRead", False),
        "has_attachments": result.get("hasAttachments", False),
        "body": result.get("body", {}).get("content", ""),
        "body_type": result.get("body", {}).get("contentType", "text"),
    }


def send_message(
    to: list[str],
    subject: str,
    body: str,
    cc: Optional[list[str]] = None,
    body_type: str = "text",
    account_name: Optional[str] = None,
) -> dict:
    """Send an email message.

    Args:
        to: List of recipient email addresses
        subject: Email subject
        body: Email body content
        cc: List of CC email addresses
        body_type: 'text' or 'html'
        account_name: Account to use

    Returns:
        Dict with success status or error
    """
    message = {
        "subject": subject,
        "body": {
            "contentType": "HTML" if body_type == "html" else "Text",
            "content": body,
        },
        "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
    }

    if cc:
        message["ccRecipients"] = [{"emailAddress": {"address": addr}} for addr in cc]

    result = graph_request("POST", "/me/sendMail", account_name, json_data={"message": message})

    if "error" in result:
        return result

    return {
        "account": resolve_account(account_name),
        "success": True,
        "to": to,
        "subject": subject,
    }


def search_messages(
    query: str,
    account_name: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Search email messages.

    Args:
        query: Search query (KQL syntax, e.g., 'from:someone@example.com')
        account_name: Account to use
        limit: Maximum results

    Returns:
        Dict with matching messages or error
    """
    params = {
        "$search": f'"{query}"',
        "$top": limit,
        "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview",
    }

    result = graph_request("GET", "/me/messages", account_name, params=params)

    if "error" in result:
        return result

    messages = []
    for m in result.get("value", []):
        from_addr = m.get("from", {}).get("emailAddress", {})
        messages.append({
            "id": m["id"],
            "subject": m.get("subject", "(No subject)"),
            "from_name": from_addr.get("name", ""),
            "from_email": from_addr.get("address", ""),
            "received": m.get("receivedDateTime"),
            "is_read": m.get("isRead", False),
            "preview": m.get("bodyPreview", "")[:150],
        })

    return {
        "account": resolve_account(account_name),
        "query": query,
        "count": len(messages),
        "messages": messages,
    }


# =============================================================================
# Calendar Functions
# =============================================================================


def list_events(
    account_name: Optional[str] = None,
    days: int = 7,
    limit: int = 50,
) -> dict:
    """List upcoming calendar events.

    Args:
        account_name: Account to use
        days: Number of days to look ahead
        limit: Maximum events to return

    Returns:
        Dict with events list or error
    """
    now = datetime.utcnow()
    time_min = now.isoformat() + "Z"
    time_max = (now + timedelta(days=days)).isoformat() + "Z"

    params = {
        "$top": limit,
        "$orderby": "start/dateTime",
        "$filter": f"start/dateTime ge '{time_min}' and start/dateTime le '{time_max}'",
        "$select": "id,subject,start,end,location,isAllDay,organizer,attendees",
    }

    result = graph_request("GET", "/me/events", account_name, params=params)

    if "error" in result:
        return result

    events = []
    for e in result.get("value", []):
        start = e.get("start", {})
        end = e.get("end", {})
        location = e.get("location", {})
        organizer = e.get("organizer", {}).get("emailAddress", {})

        events.append({
            "id": e["id"],
            "subject": e.get("subject", "(No title)"),
            "start": start.get("dateTime"),
            "start_timezone": start.get("timeZone"),
            "end": end.get("dateTime"),
            "end_timezone": end.get("timeZone"),
            "is_all_day": e.get("isAllDay", False),
            "location": location.get("displayName", ""),
            "organizer": organizer.get("address", ""),
        })

    return {
        "account": resolve_account(account_name),
        "time_min": time_min,
        "time_max": time_max,
        "count": len(events),
        "events": events,
    }


def list_events_today(account_name: Optional[str] = None) -> dict:
    """List today's calendar events.

    Args:
        account_name: Account to use

    Returns:
        Dict with events list or error
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    time_min = today_start.isoformat() + "Z"
    time_max = today_end.isoformat() + "Z"

    params = {
        "$orderby": "start/dateTime",
        "$filter": f"start/dateTime ge '{time_min}' and start/dateTime le '{time_max}'",
        "$select": "id,subject,start,end,location,isAllDay",
    }

    result = graph_request("GET", "/me/events", account_name, params=params)

    if "error" in result:
        return result

    events = []
    for e in result.get("value", []):
        start = e.get("start", {})
        end = e.get("end", {})
        location = e.get("location", {})

        events.append({
            "id": e["id"],
            "subject": e.get("subject", "(No title)"),
            "start": start.get("dateTime"),
            "end": end.get("dateTime"),
            "is_all_day": e.get("isAllDay", False),
            "location": location.get("displayName", ""),
        })

    return {
        "account": resolve_account(account_name),
        "date": today_start.strftime("%Y-%m-%d"),
        "count": len(events),
        "events": events,
    }


def create_event(
    subject: str,
    start: str,
    end: Optional[str] = None,
    duration_minutes: int = 60,
    location: Optional[str] = None,
    body: Optional[str] = None,
    attendees: Optional[list[str]] = None,
    is_all_day: bool = False,
    account_name: Optional[str] = None,
) -> dict:
    """Create a calendar event.

    Args:
        subject: Event title
        start: Start datetime (ISO format)
        end: End datetime (optional, calculated from duration if not provided)
        duration_minutes: Duration in minutes (default 60)
        location: Event location
        body: Event description
        attendees: List of attendee email addresses
        is_all_day: Whether this is an all-day event
        account_name: Account to use

    Returns:
        Dict with created event or error
    """
    # Parse start time
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    except ValueError:
        # Try other formats
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d"]:
            try:
                start_dt = datetime.strptime(start, fmt)
                break
            except ValueError:
                continue
        else:
            return {"error": f"Invalid start datetime format: {start}"}

    # Calculate end time if not provided
    if end:
        try:
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError:
            for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                try:
                    end_dt = datetime.strptime(end, fmt)
                    break
                except ValueError:
                    continue
            else:
                return {"error": f"Invalid end datetime format: {end}"}
    else:
        end_dt = start_dt + timedelta(minutes=duration_minutes)

    event_data = {
        "subject": subject,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "UTC",
        },
        "isAllDay": is_all_day,
    }

    if location:
        event_data["location"] = {"displayName": location}

    if body:
        event_data["body"] = {"contentType": "Text", "content": body}

    if attendees:
        event_data["attendees"] = [
            {"emailAddress": {"address": addr}, "type": "required"}
            for addr in attendees
        ]

    result = graph_request("POST", "/me/events", account_name, json_data=event_data)

    if "error" in result:
        return result

    return {
        "account": resolve_account(account_name),
        "id": result.get("id"),
        "subject": result.get("subject"),
        "start": result.get("start", {}).get("dateTime"),
        "end": result.get("end", {}).get("dateTime"),
        "web_link": result.get("webLink"),
    }


# =============================================================================
# Contacts Functions
# =============================================================================


def list_contacts(
    account_name: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List contacts.

    Args:
        account_name: Account to use
        limit: Maximum contacts to return

    Returns:
        Dict with contacts list or error
    """
    params = {
        "$top": limit,
        "$orderby": "displayName",
        "$select": "id,displayName,emailAddresses,mobilePhone,businessPhones,companyName,jobTitle",
    }

    result = graph_request("GET", "/me/contacts", account_name, params=params)

    if "error" in result:
        return result

    contacts = []
    for c in result.get("value", []):
        email_addrs = c.get("emailAddresses", [])
        primary_email = email_addrs[0].get("address") if email_addrs else ""

        contacts.append({
            "id": c["id"],
            "display_name": c.get("displayName", ""),
            "email": primary_email,
            "mobile_phone": c.get("mobilePhone", ""),
            "business_phone": c.get("businessPhones", [""])[0] if c.get("businessPhones") else "",
            "company": c.get("companyName", ""),
            "job_title": c.get("jobTitle", ""),
        })

    return {
        "account": resolve_account(account_name),
        "count": len(contacts),
        "contacts": contacts,
    }


def search_contacts(
    query: str,
    account_name: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Search contacts.

    Args:
        query: Search query (searches displayName and emailAddresses)
        account_name: Account to use
        limit: Maximum results

    Returns:
        Dict with matching contacts or error
    """
    # Filter by displayName containing query (case-insensitive)
    params = {
        "$top": limit,
        "$filter": f"contains(displayName, '{query}')",
        "$select": "id,displayName,emailAddresses,mobilePhone,companyName",
    }

    result = graph_request("GET", "/me/contacts", account_name, params=params)

    if "error" in result:
        return result

    contacts = []
    for c in result.get("value", []):
        email_addrs = c.get("emailAddresses", [])
        primary_email = email_addrs[0].get("address") if email_addrs else ""

        contacts.append({
            "id": c["id"],
            "display_name": c.get("displayName", ""),
            "email": primary_email,
            "mobile_phone": c.get("mobilePhone", ""),
            "company": c.get("companyName", ""),
        })

    return {
        "account": resolve_account(account_name),
        "query": query,
        "count": len(contacts),
        "contacts": contacts,
    }


# =============================================================================
# User Profile
# =============================================================================


def get_user_profile(account_name: Optional[str] = None) -> dict:
    """Get current user's profile information.

    Args:
        account_name: Account to use

    Returns:
        Dict with user profile or error
    """
    result = graph_request("GET", "/me", account_name)

    if "error" in result:
        return result

    return {
        "account": resolve_account(account_name),
        "display_name": result.get("displayName", ""),
        "email": result.get("mail") or result.get("userPrincipalName", ""),
        "job_title": result.get("jobTitle", ""),
        "office_location": result.get("officeLocation", ""),
    }
