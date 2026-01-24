# Nextcloud Integration

Integration agent for Nextcloud services.

## Capabilities

- File management via WebDAV (list, read, write, delete, move)
- Calendar access via CalDAV (list calendars, events, create/delete events)
- Deck boards and cards management

## Configuration

Configure instances in this agent's config.json under `integration.instances`.

Set passwords via environment variables:
- `NEXTCLOUD_PERSONAL_PASSWORD` for the "personal" instance
- `NEXTCLOUD_{INSTANCE_ID}_PASSWORD` for other instances

Create app passwords in Nextcloud: Settings > Security > Devices & Sessions.
