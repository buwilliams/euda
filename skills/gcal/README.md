# Google Calendar Skill

Google Calendar integration with multiple account support.

## Commands

- `gcal accounts list` - List configured accounts
- `gcal accounts add <name>` - Add account via OAuth
- `gcal accounts add-service <name> --key-file <path>` - Add service account
- `gcal accounts remove <name>` - Remove an account
- `gcal accounts default [name]` - Get/set default account
- `gcal calendars list [--account]` - List calendars
- `gcal events list [--account] [--calendar] [--days]` - List upcoming events
- `gcal events today [--account]` - Today's events across all calendars
- `gcal events create <title> --start <datetime> [options]` - Create event

## Authentication Options

### Option 1: OAuth2 (Interactive)

For personal use with interactive OAuth flow:

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID (Desktop application type)
3. Set environment variables:
   ```bash
   export GOOGLE_CLIENT_ID="your-client-id"
   export GOOGLE_CLIENT_SECRET="your-client-secret"
   ```
4. Add an account:
   ```bash
   euno skills gcal accounts add personal
   ```

### Option 2: Service Account (Backend-to-Backend)

For backend-to-backend integration, service accounts are the right approach.

#### 1. Go to Google Cloud Console

Navigate to [console.cloud.google.com](https://console.cloud.google.com) and select your project.

#### 2. Enable the Google Calendar API

- Go to **APIs & Services → Library**
- Search "Google Calendar API" and **Enable** it

#### 3. Create a Service Account

- Go to **APIs & Services → Credentials**
- Click **Create Credentials → Service account**
- Give it a name and description
- Click **Create and Continue**
- (Optional) Grant roles if needed, then click **Done**

#### 4. Generate a Key

- Click on your new service account
- Go to the **Keys** tab
- Click **Add Key → Create new key**
- Choose **JSON**
- Download and save the file securely

This JSON file contains everything you need:

```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "your-service@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  ...
}
```

#### 5. Grant Calendar Access

**Important:** Service accounts have their own identity. To access a calendar:

- **Option A (Specific calendar):** Share the calendar with the service account's email (`client_email` from the JSON) and give it appropriate permissions (read/write)

- **Option B (Google Workspace domain-wide):** If you need to access user calendars across a Workspace domain, set up domain-wide delegation in the Admin console

#### 6. Add the Service Account to Euno

```bash
euno skills gcal accounts add-service backend --key-file /path/to/service-account-key.json
```

The skill will copy the key file to its data directory and display the service account email. Share your calendar with this email to grant access.

## Data Storage

Tokens and config are stored in `data/plugins/gcal/`:

```
data/plugins/gcal/
├── config.json                 # Plugin config (default account)
└── accounts/
    ├── personal/
    │   └── token.json          # OAuth2 tokens
    ├── work/
    │   └── token.json
    └── backend/
        └── service_account.json  # Service account key
```
