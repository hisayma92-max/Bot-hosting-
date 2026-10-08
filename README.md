# Telegram HTML + Bot Hosting Bot

## Included
- Image/profile-based welcome message with user ID, username, status, package and file quota.
- Free `.html` hosting with public URL.
- Hosting packages and upgrade requests.
- Admin-only panel for Telegram user ID `7740120627`.
- Admin statistics, latest users, pending upgrades and database info.
- Admin **New Update** button: write an update and broadcast it to registered users; the latest update is saved in SQLite.
- Admin **Broadcast** button for general announcements.
- `/approve REQUEST_ID`, `/reject REQUEST_ID`, `/setpackage USER_ID free|basic|pro|premium`.
- SQLite database at `data/bot.db` plus `database.sql` schema.

## Very important: Bot token security
The BotFather token pasted into chat is a secret credential. Do **not** put that exposed token in the project. Revoke/regenerate it in BotFather and place the new token only in your server's `.env` file.

## Setup
1. Install Python 3.11+.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`.
4. Put the **new** BotFather token in `.env`.
5. Keep `ADMIN_ID=7740120627`.
6. Set `PUBLIC_BASE_URL` to your HTTPS domain.
7. Run `python bot.py`.

## Updates Channel
A normal public channel URL does not create a Telegram join-request flow. For actual join requests, create a channel invite link with approval/join-request enabled and put that invite link into `UPDATES_INVITE_LINK`.

## Security
This starter does not execute arbitrary uploaded Python/JavaScript files. Real script hosting should use isolated containers/sandboxes with strict CPU/RAM/time/network limits. Never execute user uploads directly on the host.
