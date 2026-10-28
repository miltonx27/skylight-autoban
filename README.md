# SKYLiGHT Auto-Ban for Nicotine+

**Unofficial Nicotine+ plugin · v1.2.0 · GPL-3.0-or-later**

Automatically check selected Soulseek search-result users for a configurable profile signature, then ban and optionally ignore matching accounts. Made for recurring profiles that appear under changing usernames.

> Unofficial community project. Not affiliated with or endorsed by Nicotine+ or Soulseek.

## Download

[Download the v1.2.0 plugin ZIP](downloads/SKYLiGHT_AutoBan_NicotinePlus_v1_2_0.zip)

## Features

- Watches Nicotine+ search-result events.
- By default, checks users whose returned paths contain `DASH`.
- Requests profile information through Nicotine+'s built-in User Info service.
- Matches profile descriptions case-insensitively, with `SKYLiGHT` and `skylight.beer` as defaults.
- Automatically bans matches and, by default, adds them to the ignore list.
- Limits concurrent profile requests and logs requests, timeouts, matches, and actions.
- No telemetry and no external HTTP requests.

## Installation

1. Download and extract the plugin ZIP.
2. Close Nicotine+ and remove any older `skylight_autoban` copy.
3. Place the `skylight_autoban` folder into the Nicotine+ plugins directory:
   - **Windows:** `%APPDATA%\nicotine\plugins\skylight_autoban\`
   - **Linux:** `~/.local/share/nicotine/plugins/skylight_autoban/`
   - **macOS:** `~/Library/Application Support/nicotine/plugins/skylight_autoban/`
4. Ensure `__init__.py` and `PLUGININFO` are directly inside `skylight_autoban`.
5. Restart Nicotine+, open **Settings → General → Plugins**, enable **SKYLiGHT Auto-Ban**, and apply.
6. Search for matching results and monitor the Nicotine+ log.

## How it works

1. A search result path contains the configured release marker (default: `DASH`).
2. The plugin queues that username and requests their profile.
3. The description is compared with configured phrases.
4. When a phrase matches, the username is added to Nicotine+'s persistent ban list and, by default, its ignore list.

### Settings

| Setting | Default | Purpose |
|---|---|---|
| `profile_keywords` | `SKYLiGHT`, `skylight.beer` | Case-insensitive phrases checked in profile descriptions |
| `release_group_marker` | `DASH` | Only checks result users whose paths contain this marker. Empty string checks every result user and may create many requests. |
| `also_ignore` | `true` | Also add matches to the ignore list |
| `max_concurrent_profiles` | `3` | Concurrent profile requests |
| `profile_timeout_seconds` | `8` | Timeout before the queue advances |

## Screenshot

The following screenshot shows the successful automatic profile detection and ban action confirmed by the maintainer.

![Redacted Nicotine+ log showing automatic profile detection](assets/detection-confirmed.png)

## Troubleshooting

Look for log messages indicating that a result matched the marker, that the profile was requested, and finally that the profile matched and was banned/ignored.

If no profile checks start, confirm the plugin is enabled and the path includes the configured marker. A timeout means the profile response did not arrive in time.

## Limitations and privacy

- A user must appear in a search result with a matching path and return profile information before the plugin can detect them.
- It bans usernames, not IP addresses. New usernames are detected as they appear.
- Changed profile wording or release tags may evade the default rules.
- The plugin makes no external HTTP requests and sends no telemetry.
- Review settings carefully to avoid unintended matches.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
