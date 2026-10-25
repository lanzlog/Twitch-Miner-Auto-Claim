# Twitch Miner Auto Claim

Headless Twitch drops miner for a VPS: no browser, no X11, ~26 MB RAM, auto-claims rewards.
Built as a thin headless wrapper around [DevilXD/TwitchDropsMiner](https://github.com/DevilXD/TwitchDropsMiner)
(GPL-3.0, cloned separately — not vendored here).

```
Drop progress from GQL: Dragonfire Chest (Albion Online, 179/180)
Claimed drop: Albion Online Dragonfire Chest (1/1)
```

## Why this exists

Running TwitchDropsMiner on a server normally means tkinter + Xvfb + pystray + PIL. This repo
replaces the GUI with a headless stub and fixes three real blockers found while running it 24/7:

1. **Device-code login for the WEB/ANDROID clients is dead**
   `POST https://id.twitch.tv/oauth2/device` → `{"status":400,"message":"invalid client"}`.
   The `SMARTBOX` client (`ue6666qo983tsx6so1t0vnawi233wa`) still works, so the login flow here
   uses it.
2. **Browser `auth-token` cannot read campaigns anymore**
   It logs in fine, then `currentUser.dropCampaigns` returns `IntegrityCheckFailed`. A token from
   `POST https://gql.twitch.tv/integrity` does not help (tried as `X-Integrity`,
   `Client-Integrity`, with/without device/session ids — all rejected). SMARTBOX passes without it.
3. **Cookie scope mismatch** — SMARTBOX's client URL is `https://android.tv.twitch.tv`, so an
   `auth-token` cookie stored for `twitch.tv` is invisible and the miner silently falls back to
   interactive login. `set_auth_smartbox.py` writes it against the right URL.

It also stubs every GUI entry point the engine touches. Missing one (`gui.channels.remove`, only
called from the *hourly* maintenance cleanup) kills the process an hour after a clean start, so
each stub class also has a `__getattr__` no-op fallback.

## Requirements

- Linux with systemd (tested on Ubuntu arm64, Python 3.11)
- A Twitch account, linked to the game you want to mine (e.g. Albion Online → Twitch connection)

## Install

```bash
sudo apt-get install -y python3-venv git
git clone https://github.com/lanzlog/Twich-Miner-Auto-Claim.git ~/twitch-miner
cd ~/twitch-miner
python3 -m venv env
env/bin/pip install -q aiohttp yarl python-dateutil pillow

# engine (GPL-3.0, kept out of this repo)
git clone --depth 1 https://github.com/DevilXD/TwitchDropsMiner.git
```

## Login (once, ~30 s)

```bash
cd ~/twitch-miner
env/bin/python smartbox_login.py
# ACTIVATE_URL: https://www.twitch.tv/activate
# ACTIVATE_CODE: XXXXXXXX
```

Open the URL, enter the code, wait for `LOGIN_OK: token stored`.
It writes `token.json` (0600) and, through `set_auth_smartbox.py`, `cookies.jar` (0600).

There is no usable refresh token for this client (`grant_type=refresh_token` →
`400 missing client secret`); when the token dies, run `smartbox_login.py` again.

## Scope it to one game

`run_headless.py` pins the client and the game scope:

```python
from constants import ClientType, PriorityMode
twitch._client_type = ClientType.SMARTBOX
twitch.settings.priority_mode = PriorityMode.PRIORITY_ONLY
twitch.settings.priority = ["Albion Online"]   # change me
twitch.settings.exclude = set()
twitch.settings.available_drops_check = True
```

`available_drops_check=True` is what makes it discover drops from live channels (not just the
dashboard), so it finds a streamer by itself and switches when one goes offline.

## Run by hand

```bash
cd ~/twitch-miner
MINER_VERBOSE=1 env/bin/python run_headless.py    # MINER_DEBUG=1 for tracebacks
```

Verify it is *actually* mining — "Watching: …" alone is not proof, the minute counter must rise:

```bash
grep -E "Watching:|Drop progress|Claimed drop" miner.log | tail -5
```

## Run daily on a timer (8 h/day)

`twitch-miner.service` starts `daily_window.sh`, which keeps the miner alive for an 8-hour budget
(restart on crash, 30 s backoff, max 20 attempts) and stops early on a clean exit or a missing
token. `twitch-miner-daily.timer` starts it once a day.

```bash
sudo cp twitch-miner.service twitch-miner-daily.timer /etc/systemd/system/
# %h in the unit resolves to the service user's home; run it as your own user:
sudo sed -i "s|^Type=simple|Type=simple\nUser=$USER|" /etc/systemd/system/twitch-miner.service
sudo systemctl daemon-reload
sudo systemctl enable --now twitch-miner-daily.timer
systemctl list-timers twitch-miner-daily.timer    # confirm NEXT in your timezone
systemctl status twitch-miner
```

Edit `OnCalendar` in the timer for your window. Keep the explicit timezone suffix
(`18:00:00 Asia/Jakarta`) if the host runs UTC, otherwise the window shifts by your offset.
Do **not** combine `Restart=always` with `RuntimeMaxSec`: systemd treats the runtime kill as a
failure and relaunches, turning the window into an endless loop.

## Claiming

Automatic. The engine claims on every inventory refresh and on `drop-claim` websocket events; the
proof line is `Claimed drop: <game> <reward> (n/m)`. No clicking, no manual inventory step.

## Files

| File | Purpose |
|---|---|
| `run_headless.py` | entrypoint: injects the stub GUI, pins SMARTBOX client + game scope |
| `headless_gui.py` | no-op GUI implementation (status, progress ticker, tray, channels, inventory, login) |
| `smartbox_login.py` | SMARTBOX device-code login → `token.json` |
| `set_auth_smartbox.py` | writes `cookies.jar` for `android.tv.twitch.tv` |
| `daily_window.sh` | 8 h window with in-window crash recovery |
| `twitch-miner.service` / `.timer` | systemd units |

## Notes & limits

- Twitch changes this API often; if login or campaign discovery breaks, check the engine repo's
  issues first, then re-probe the OAuth endpoints before assuming the wrapper is at fault.
- Drops only accrue for campaigns the account is eligible for and for channels that are live with
  drops enabled.
- `miner.log` is not rotated by the app; add logrotate if you keep verbose logging on.
- No credentials are stored in this repo. `token.json`, `cookies.jar`, `miner.log`, `env/` and the
  engine checkout are git-ignored.

## License

MIT for the files in this repo. The engine (`TwitchDropsMiner`) is GPL-3.0 and is cloned at
runtime; it is not redistributed here.
