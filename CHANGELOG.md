# Changelog

## 1.2.0

- Uses Nicotine+'s built-in User Info service instead of importing internal protocol message classes.
- Automatically queues profile checks for search-result paths matching the configured release marker.
- Matches configurable profile phrases case-insensitively.
- Automatically bans matches and optionally ignores them.
- Limits concurrent profile requests and advances after timeouts.
- Adds diagnostic logging for search markers, profile requests, matches, and actions.

## 1.1.0

- Added automatic profile checks from matching search-result paths.
- Added profile keyword matching and ban/ignore actions.

## 1.0.0

- Initial profile-description matching implementation.
