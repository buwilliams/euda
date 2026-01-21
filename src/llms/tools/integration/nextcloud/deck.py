"""
Nextcloud Deck Tools - Kanban board operations via REST API.
"""

import json
import requests

from ... import tool
from .client import get_client, NextcloudConfigError


@tool(
    "nc_list_boards",
    "List Nextcloud Deck boards. Use when: viewing kanban boards.",
    tool_type="integration"
)
def nc_list_boards(instance: str = None) -> dict:
    """List all Deck boards.

    Args:
        instance: Nextcloud instance ID

    Returns:
        Dict with boards list or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    try:
        resp = client.deck_request("GET", "/boards")

        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code == 404:
            return {"error": "Deck app not installed or not accessible"}
        if resp.status_code != 200:
            return {"error": f"Request failed with status {resp.status_code}"}

        boards = resp.json()

        # Simplify board data
        result = []
        for board in boards:
            result.append({
                "id": board.get("id"),
                "title": board.get("title"),
                "color": board.get("color"),
                "archived": board.get("archived", False),
                "owner": board.get("owner", {}).get("displayname")
            })

        return {
            "boards": result,
            "count": len(result),
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from server"}


@tool(
    "nc_get_board",
    "Get details of a Deck board including stacks and cards. Use when: viewing board contents.",
    tool_type="integration"
)
def nc_get_board(board_id: int, instance: str = None) -> dict:
    """Get board details with stacks.

    Args:
        board_id: Board ID number
        instance: Nextcloud instance ID

    Returns:
        Dict with board details, stacks, and cards or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    try:
        # Get board details
        resp = client.deck_request("GET", f"/boards/{board_id}")

        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code == 404:
            return {"error": f"Board not found: {board_id}"}
        if resp.status_code != 200:
            return {"error": f"Request failed with status {resp.status_code}"}

        board = resp.json()

        # Get stacks for this board
        stacks_resp = client.deck_request("GET", f"/boards/{board_id}/stacks")

        if stacks_resp.status_code != 200:
            return {"error": f"Failed to get stacks: {stacks_resp.status_code}"}

        stacks = stacks_resp.json()

        # Format stacks with their cards
        formatted_stacks = []
        for stack in stacks:
            cards = []
            for card in stack.get("cards", []):
                cards.append({
                    "id": card.get("id"),
                    "title": card.get("title"),
                    "description": card.get("description"),
                    "due_date": card.get("duedate"),
                    "order": card.get("order"),
                    "archived": card.get("archived", False)
                })

            formatted_stacks.append({
                "id": stack.get("id"),
                "title": stack.get("title"),
                "order": stack.get("order"),
                "cards": cards,
                "card_count": len(cards)
            })

        return {
            "board": {
                "id": board.get("id"),
                "title": board.get("title"),
                "color": board.get("color"),
                "archived": board.get("archived", False)
            },
            "stacks": formatted_stacks,
            "stack_count": len(formatted_stacks),
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from server"}


@tool(
    "nc_list_cards",
    "List cards in a Deck stack. Use when: viewing tasks in a column.",
    tool_type="integration"
)
def nc_list_cards(board_id: int, stack_id: int, instance: str = None) -> dict:
    """List cards in a stack.

    Args:
        board_id: Board ID
        stack_id: Stack ID
        instance: Nextcloud instance ID

    Returns:
        Dict with cards list or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    try:
        # Get the specific stack which includes its cards
        resp = client.deck_request("GET", f"/boards/{board_id}/stacks/{stack_id}")

        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code == 404:
            return {"error": f"Stack not found: board={board_id}, stack={stack_id}"}
        if resp.status_code != 200:
            return {"error": f"Request failed with status {resp.status_code}"}

        stack = resp.json()

        cards = []
        for card in stack.get("cards", []):
            cards.append({
                "id": card.get("id"),
                "title": card.get("title"),
                "description": card.get("description"),
                "due_date": card.get("duedate"),
                "order": card.get("order"),
                "archived": card.get("archived", False),
                "labels": [l.get("title") for l in card.get("labels", [])]
            })

        return {
            "board_id": board_id,
            "stack": {
                "id": stack.get("id"),
                "title": stack.get("title")
            },
            "cards": cards,
            "count": len(cards),
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from server"}


@tool(
    "nc_create_card",
    "Create a card in Nextcloud Deck. Use when: adding tasks to a board.",
    tool_type="integration"
)
def nc_create_card(
    board_id: int,
    stack_id: int,
    title: str,
    description: str = None,
    due_date: str = None,
    instance: str = None
) -> dict:
    """Create a new card.

    Args:
        board_id: Board ID
        stack_id: Stack ID to place card in
        title: Card title
        description: Card description (markdown supported)
        due_date: Due date (ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        instance: Nextcloud instance ID

    Returns:
        Dict with card details or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    try:
        # Build card data
        card_data = {
            "title": title,
            "type": "plain",
            "order": 999  # Will be placed at the end
        }

        if description:
            card_data["description"] = description

        if due_date:
            card_data["duedate"] = due_date

        resp = client.deck_request(
            "POST",
            f"/boards/{board_id}/stacks/{stack_id}/cards",
            data=json.dumps(card_data)
        )

        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code == 404:
            return {"error": f"Board or stack not found: board={board_id}, stack={stack_id}"}
        if resp.status_code not in (200, 201):
            return {"error": f"Request failed with status {resp.status_code}"}

        card = resp.json()

        return {
            "status": "created",
            "card": {
                "id": card.get("id"),
                "title": card.get("title"),
                "description": card.get("description"),
                "due_date": card.get("duedate"),
                "stack_id": stack_id,
                "board_id": board_id
            },
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from server"}


@tool(
    "nc_update_card",
    "Update a Deck card's details. Use when: modifying task information.",
    tool_type="integration"
)
def nc_update_card(
    board_id: int,
    stack_id: int,
    card_id: int,
    title: str = None,
    description: str = None,
    due_date: str = None,
    instance: str = None
) -> dict:
    """Update card details.

    Args:
        board_id: Board ID
        stack_id: Stack ID containing the card
        card_id: Card ID to update
        title: New title (optional)
        description: New description (optional)
        due_date: New due date (optional, ISO format)
        instance: Nextcloud instance ID

    Returns:
        Dict with updated card or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    # Check if any updates provided
    if title is None and description is None and due_date is None:
        return {"error": "No updates provided. Specify title, description, or due_date."}

    try:
        # First get current card to preserve existing data
        get_resp = client.deck_request(
            "GET",
            f"/boards/{board_id}/stacks/{stack_id}/cards/{card_id}"
        )

        if get_resp.status_code == 404:
            return {"error": f"Card not found: {card_id}"}
        if get_resp.status_code != 200:
            return {"error": f"Failed to get card: {get_resp.status_code}"}

        current = get_resp.json()

        # Build update data
        update_data = {
            "title": title if title is not None else current.get("title"),
            "type": current.get("type", "plain"),
            "order": current.get("order", 0),
            "description": description if description is not None else current.get("description", ""),
            "duedate": due_date if due_date is not None else current.get("duedate")
        }

        resp = client.deck_request(
            "PUT",
            f"/boards/{board_id}/stacks/{stack_id}/cards/{card_id}",
            data=json.dumps(update_data)
        )

        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code == 404:
            return {"error": f"Card not found: {card_id}"}
        if resp.status_code != 200:
            return {"error": f"Request failed with status {resp.status_code}"}

        card = resp.json()

        return {
            "status": "updated",
            "card": {
                "id": card.get("id"),
                "title": card.get("title"),
                "description": card.get("description"),
                "due_date": card.get("duedate"),
                "stack_id": stack_id,
                "board_id": board_id
            },
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from server"}


@tool(
    "nc_move_card",
    "Move a card to a different stack in Deck. Use when: updating task status.",
    tool_type="integration"
)
def nc_move_card(
    board_id: int,
    card_id: int,
    target_stack_id: int,
    instance: str = None
) -> dict:
    """Move card to another stack.

    Args:
        board_id: Board ID
        card_id: Card ID to move
        target_stack_id: Destination stack ID
        instance: Nextcloud instance ID

    Returns:
        Dict with updated card or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    try:
        # Deck API uses reorder endpoint for moving cards between stacks
        move_data = {
            "stackId": target_stack_id,
            "order": 999  # Place at end of target stack
        }

        resp = client.deck_request(
            "PUT",
            f"/boards/{board_id}/stacks/{target_stack_id}/cards/{card_id}/reorder",
            data=json.dumps(move_data)
        )

        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code == 404:
            return {"error": f"Card or stack not found: card={card_id}, stack={target_stack_id}"}
        if resp.status_code != 200:
            return {"error": f"Request failed with status {resp.status_code}"}

        card = resp.json()

        return {
            "status": "moved",
            "card": {
                "id": card.get("id"),
                "title": card.get("title"),
                "stack_id": target_stack_id,
                "board_id": board_id
            },
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from server"}


@tool(
    "nc_delete_card",
    "Delete a card from Nextcloud Deck. Use when: removing tasks from a board.",
    tool_type="integration"
)
def nc_delete_card(
    board_id: int,
    stack_id: int,
    card_id: int,
    instance: str = None
) -> dict:
    """Delete a card.

    Args:
        board_id: Board ID
        stack_id: Stack ID containing the card
        card_id: Card ID to delete
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    try:
        resp = client.deck_request(
            "DELETE",
            f"/boards/{board_id}/stacks/{stack_id}/cards/{card_id}"
        )

        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code == 404:
            return {"error": f"Card not found: {card_id}"}
        if resp.status_code not in (200, 204):
            return {"error": f"Request failed with status {resp.status_code}"}

        return {
            "status": "deleted",
            "card_id": card_id,
            "board_id": board_id,
            "stack_id": stack_id,
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
