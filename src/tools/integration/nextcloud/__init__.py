"""
Nextcloud Integration - Tools for interacting with Nextcloud servers.

Supports multiple Nextcloud instances configured in data/system/config.json.
Credentials are loaded from environment variables (NEXTCLOUD_{INSTANCE}_PASSWORD).

Tools:
- Files (WebDAV): nc_list_files, nc_read_file, nc_write_file, nc_delete_file,
                  nc_create_folder, nc_move_file
- Calendar (CalDAV): nc_list_calendars, nc_list_events, nc_create_event, nc_delete_event
- Deck (REST API): nc_list_boards, nc_get_board, nc_list_cards, nc_create_card,
                   nc_update_card, nc_move_card, nc_delete_card
- Utility: nc_list_instances
"""

from . import files, calendar, deck
