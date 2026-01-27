"""Nextcloud Deck operations for the nextcloud plugin."""

from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_deck_module():
    """Lazy import of nextcloud deck module."""
    from plugins.nextcloud.lib.deck import (
        nc_list_boards, nc_get_board, nc_list_cards,
        nc_create_card, nc_update_card, nc_move_card, nc_delete_card
    )
    return {
        "nc_list_boards": nc_list_boards,
        "nc_get_board": nc_get_board,
        "nc_list_cards": nc_list_cards,
        "nc_create_card": nc_create_card,
        "nc_update_card": nc_update_card,
        "nc_move_card": nc_move_card,
        "nc_delete_card": nc_delete_card,
    }


@app.command("boards")
def boards_cmd(
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """List all Deck boards."""
    m = _get_deck_module()
    result = m["nc_list_boards"](instance=instance)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Instance: {result.get('instance')}")
    print(f"Boards ({result.get('count', 0)}):")

    for board in result.get("boards", []):
        archived = " [archived]" if board.get("archived") else ""
        print(f"  [{board.get('id')}] {board.get('title')}{archived}")


@app.command("board")
def board_cmd(
    board_id: int = typer.Argument(..., help="Board ID"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Get board details with stacks and cards."""
    m = _get_deck_module()
    result = m["nc_get_board"](board_id=board_id, instance=instance)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    board = result.get("board", {})
    print(f"Board: {board.get('title')} (ID: {board.get('id')})")
    print(f"Instance: {result.get('instance')}")
    print(f"\nStacks ({result.get('stack_count', 0)}):")

    for stack in result.get("stacks", []):
        print(f"\n  [{stack.get('id')}] {stack.get('title')} ({stack.get('card_count', 0)} cards)")
        for card in stack.get("cards", []):
            due = f" (due: {card.get('due_date')})" if card.get("due_date") else ""
            print(f"    - [{card.get('id')}] {card.get('title')}{due}")


@app.command("cards")
def cards_cmd(
    board_id: int = typer.Argument(..., help="Board ID"),
    stack_id: int = typer.Argument(..., help="Stack ID"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """List cards in a stack."""
    m = _get_deck_module()
    result = m["nc_list_cards"](board_id=board_id, stack_id=stack_id, instance=instance)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    stack = result.get("stack", {})
    print(f"Stack: {stack.get('title')} (ID: {stack.get('id')})")
    print(f"Cards ({result.get('count', 0)}):")

    for card in result.get("cards", []):
        labels = f" [{', '.join(card.get('labels', []))}]" if card.get("labels") else ""
        due = f" (due: {card.get('due_date')})" if card.get("due_date") else ""
        print(f"  [{card.get('id')}] {card.get('title')}{labels}{due}")


@app.command("create-card")
def create_card_cmd(
    board_id: int = typer.Argument(..., help="Board ID"),
    stack_id: int = typer.Argument(..., help="Stack ID"),
    title: str = typer.Argument(..., help="Card title"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Card description"),
    due_date: Optional[str] = typer.Option(None, "--due", help="Due date (ISO format)"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Create a new card."""
    m = _get_deck_module()
    result = m["nc_create_card"](
        board_id=board_id,
        stack_id=stack_id,
        title=title,
        description=description,
        due_date=due_date,
        instance=instance
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    card = result.get("card", {})
    print(f"Created card: {card.get('title')}")
    print(f"ID: {card.get('id')}")
    print(f"Stack: {card.get('stack_id')}")


@app.command("update-card")
def update_card_cmd(
    board_id: int = typer.Argument(..., help="Board ID"),
    stack_id: int = typer.Argument(..., help="Stack ID"),
    card_id: int = typer.Argument(..., help="Card ID"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    due_date: Optional[str] = typer.Option(None, "--due", help="New due date"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Update a card's details."""
    m = _get_deck_module()
    result = m["nc_update_card"](
        board_id=board_id,
        stack_id=stack_id,
        card_id=card_id,
        title=title,
        description=description,
        due_date=due_date,
        instance=instance
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    card = result.get("card", {})
    print(f"Updated card: {card.get('title')} (ID: {card.get('id')})")


@app.command("move-card")
def move_card_cmd(
    board_id: int = typer.Argument(..., help="Board ID"),
    card_id: int = typer.Argument(..., help="Card ID"),
    target_stack_id: int = typer.Argument(..., help="Destination stack ID"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Move a card to another stack."""
    m = _get_deck_module()
    result = m["nc_move_card"](
        board_id=board_id,
        card_id=card_id,
        target_stack_id=target_stack_id,
        instance=instance
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    card = result.get("card", {})
    print(f"Moved card: {card.get('title')} to stack {card.get('stack_id')}")


@app.command("delete-card")
def delete_card_cmd(
    board_id: int = typer.Argument(..., help="Board ID"),
    stack_id: int = typer.Argument(..., help="Stack ID"),
    card_id: int = typer.Argument(..., help="Card ID"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Delete a card."""
    m = _get_deck_module()
    result = m["nc_delete_card"](
        board_id=board_id,
        stack_id=stack_id,
        card_id=card_id,
        instance=instance
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Deleted card: {result.get('card_id')}")
