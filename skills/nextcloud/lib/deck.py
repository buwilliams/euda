"""Nextcloud Deck (kanban board) operations."""

import json
from typing import Optional

from .client import NextcloudClient


def _api_request(
    client: NextcloudClient,
    method: str,
    path: str,
    data: Optional[dict] = None
) -> tuple[int, dict]:
    """Make a Deck API request.

    Args:
        client: NextcloudClient instance
        method: HTTP method
        path: API path (without /index.php/apps/deck/api/v1.0/)
        data: JSON data to send

    Returns:
        Tuple of (status_code, response_dict)
    """
    api_path = f"/index.php/apps/deck/api/v1.0/{path}"

    headers = {
        "OCS-APIRequest": "true",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    body = json.dumps(data).encode() if data else None

    status, response_body, _ = client.request(method, api_path, data=body, headers=headers)

    try:
        response_data = json.loads(response_body.decode()) if response_body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        response_data = {}

    return status, response_data


def nc_list_boards(instance: Optional[str] = None) -> dict:
    """List all Deck boards.

    Args:
        instance: Nextcloud instance ID

    Returns:
        Dict with boards list or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    try:
        status, data = _api_request(client, "GET", "boards")
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 401:
        return {"error": "Authentication failed"}
    if status != 200:
        return {"error": f"Server returned status {status}"}

    boards = []
    for board in data if isinstance(data, list) else []:
        boards.append({
            "id": board.get("id"),
            "title": board.get("title"),
            "archived": board.get("archived", False),
            "color": board.get("color"),
        })

    return {
        "instance": client.instance_id,
        "boards": boards,
        "count": len(boards),
    }


def nc_get_board(board_id: int, instance: Optional[str] = None) -> dict:
    """Get board details with stacks and cards.

    Args:
        board_id: Board ID
        instance: Nextcloud instance ID

    Returns:
        Dict with board details or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    # Get board info
    try:
        status, board_data = _api_request(client, "GET", f"boards/{board_id}")
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Board not found: {board_id}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status != 200:
        return {"error": f"Server returned status {status}"}

    # Get stacks with cards
    try:
        status, stacks_data = _api_request(client, "GET", f"boards/{board_id}/stacks")
    except ConnectionError as e:
        return {"error": str(e)}

    if status != 200:
        stacks_data = []

    stacks = []
    for stack in stacks_data if isinstance(stacks_data, list) else []:
        cards = []
        for card in stack.get("cards", []):
            cards.append({
                "id": card.get("id"),
                "title": card.get("title"),
                "due_date": card.get("duedate"),
                "labels": [l.get("title") for l in card.get("labels", [])],
            })

        stacks.append({
            "id": stack.get("id"),
            "title": stack.get("title"),
            "order": stack.get("order"),
            "cards": cards,
            "card_count": len(cards),
        })

    return {
        "board": {
            "id": board_data.get("id"),
            "title": board_data.get("title"),
            "archived": board_data.get("archived", False),
        },
        "instance": client.instance_id,
        "stacks": stacks,
        "stack_count": len(stacks),
    }


def nc_list_cards(
    board_id: int,
    stack_id: int,
    instance: Optional[str] = None
) -> dict:
    """List cards in a stack.

    Args:
        board_id: Board ID
        stack_id: Stack ID
        instance: Nextcloud instance ID

    Returns:
        Dict with cards list or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    try:
        status, data = _api_request(client, "GET", f"boards/{board_id}/stacks/{stack_id}")
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Stack not found: board={board_id}, stack={stack_id}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status != 200:
        return {"error": f"Server returned status {status}"}

    cards = []
    for card in data.get("cards", []):
        cards.append({
            "id": card.get("id"),
            "title": card.get("title"),
            "description": card.get("description"),
            "due_date": card.get("duedate"),
            "labels": [l.get("title") for l in card.get("labels", [])],
            "order": card.get("order"),
        })

    return {
        "stack": {
            "id": data.get("id"),
            "title": data.get("title"),
        },
        "instance": client.instance_id,
        "cards": cards,
        "count": len(cards),
    }


def nc_create_card(
    board_id: int,
    stack_id: int,
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    instance: Optional[str] = None
) -> dict:
    """Create a new card.

    Args:
        board_id: Board ID
        stack_id: Stack ID
        title: Card title
        description: Card description
        due_date: Due date (ISO format)
        instance: Nextcloud instance ID

    Returns:
        Dict with created card info or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    card_data = {"title": title, "type": "plain"}
    if description:
        card_data["description"] = description
    if due_date:
        card_data["duedate"] = due_date

    try:
        status, data = _api_request(
            client, "POST", f"boards/{board_id}/stacks/{stack_id}/cards", card_data
        )
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Stack not found: board={board_id}, stack={stack_id}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status not in (200, 201):
        return {"error": f"Server returned status {status}"}

    return {
        "card": {
            "id": data.get("id"),
            "title": data.get("title"),
            "stack_id": stack_id,
        },
        "instance": client.instance_id,
    }


def nc_update_card(
    board_id: int,
    stack_id: int,
    card_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    instance: Optional[str] = None
) -> dict:
    """Update a card's details.

    Args:
        board_id: Board ID
        stack_id: Stack ID
        card_id: Card ID
        title: New title
        description: New description
        due_date: New due date
        instance: Nextcloud instance ID

    Returns:
        Dict with updated card info or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    update_data = {"type": "plain"}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if due_date is not None:
        update_data["duedate"] = due_date

    try:
        status, data = _api_request(
            client, "PUT", f"boards/{board_id}/stacks/{stack_id}/cards/{card_id}", update_data
        )
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Card not found: {card_id}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status != 200:
        return {"error": f"Server returned status {status}"}

    return {
        "card": {
            "id": data.get("id"),
            "title": data.get("title"),
            "stack_id": stack_id,
        },
        "instance": client.instance_id,
    }


def nc_move_card(
    board_id: int,
    card_id: int,
    target_stack_id: int,
    instance: Optional[str] = None
) -> dict:
    """Move a card to another stack.

    Args:
        board_id: Board ID
        card_id: Card ID
        target_stack_id: Destination stack ID
        instance: Nextcloud instance ID

    Returns:
        Dict with moved card info or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    # Deck API uses a reorder endpoint for moving cards
    move_data = {"stackId": target_stack_id, "order": 0}

    try:
        status, data = _api_request(
            client, "PUT", f"boards/{board_id}/stacks/{target_stack_id}/cards/{card_id}/reorder", move_data
        )
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Card not found: {card_id}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status != 200:
        return {"error": f"Server returned status {status}"}

    return {
        "card": {
            "id": card_id,
            "title": data.get("title", ""),
            "stack_id": target_stack_id,
        },
        "instance": client.instance_id,
    }


def nc_delete_card(
    board_id: int,
    stack_id: int,
    card_id: int,
    instance: Optional[str] = None
) -> dict:
    """Delete a card.

    Args:
        board_id: Board ID
        stack_id: Stack ID
        card_id: Card ID
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    try:
        status, _ = _api_request(
            client, "DELETE", f"boards/{board_id}/stacks/{stack_id}/cards/{card_id}"
        )
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Card not found: {card_id}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status not in (200, 204):
        return {"error": f"Server returned status {status}"}

    return {
        "status": "deleted",
        "card_id": card_id,
        "instance": client.instance_id,
    }
