# Study Buddy Bot

A Telegram bot that connects students based on shared subjects, facilitating collaboration through smart matchmaking.

## Features

* **Interactive Registration**: Multi-step setup (name → subjects → role → availability).
* **Smart Matchmaking**: Finds peers by shared subjects and skips already-seen users.
* **Connect / Skip**: One-tap inline buttons to manage potential study buddies.
* **Profile Management**: View your info and track connection count.
* **SQLite Backend**: Lightweight, zero-config data storage.

## Quick Start

### 1. Clone and Setup

git clone <repo-url>
cd study_buddy_bot

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate 

pip install -r requirements.txt

### 2. Configure Token

Set your bot token (from [@BotFather](https://t.me/BotFather)) as an environment variable:

export BOT_TOKEN="your-token-here"

*(Alternatively, edit `BOT_TOKEN` directly in `config.py`)*

### 3. Run

python bot.py

## Commands

* `/start` — Create or update your profile
* `/find` — Find study buddies with matching subjects
* `/profile` — View your current profile
* `/help` — Show all commands
* `/cancel` — Cancel the current action

## Configuration (`config.py`)

You can customize the bot's behavior in `config.py`:
* `MAX_MATCHES`: Max users shown per `/find` request (default: 5).
* `SUBJECTS`: Edit the list to add or remove available study topics.
