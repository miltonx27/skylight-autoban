# SPDX-License-Identifier: Apache-2.0
"""Automatically detect and ban SKYLiGHT-style Soulseek profile accounts."""

from collections import deque

from pynicotine.events import events
from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):
    """Probe matching search-result users and ban matching profile descriptions.

    SKYLiGHT profiles are identified from their profile description, not their
    mutable username. To avoid requesting every search result user's profile,
    the plugin only probes users whose result paths contain a configured release
    marker (DASH by default). It also checks profile responses opened manually.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = {
            "profile_keywords": ["SKYLiGHT", "skylight.beer"],
            "release_group_marker": "DASH",
            "also_ignore": True,
            "max_concurrent_profiles": 3,
            "profile_timeout_seconds": 8,
        }
        self.metasettings = {
            "profile_keywords": {
                "description": (
                    "Case-insensitive phrases in the profile description that trigger a ban. "
                    "Keep SKYLiGHT as a keyword; each list entry is a separate match."
                ),
                "group": "Detection",
                "type": "list string",
            },
            "release_group_marker": {
                "description": (
                    "Only automatically request profiles from search-result users whose returned "
                    "file paths contain this marker. DASH targets the release tag seen in SKYLiGHT results. "
                    "Leave blank to probe every search-result user (not recommended)."
                ),
                "group": "Automatic profile checks",
                "type": "string",
            },
            "max_concurrent_profiles": {
                "description": "Maximum profile requests in flight at once.",
                "group": "Automatic profile checks",
                "type": "int",
                "minimum": 1,
            },
            "profile_timeout_seconds": {
                "description": "Seconds to wait for a profile response before moving on.",
                "group": "Automatic profile checks",
                "type": "int",
                "minimum": 2,
            },
            "also_ignore": {
                "description": "Also add matching users to Nicotine+'s ignore list to hide future search results.",
                "group": "Actions",
                "type": "bool",
            },
        }

        self._profile_queue = deque()
        self._queued_users = set()
        self._requested_users = set()
        self._checked_users = set()
        self._inflight = {}
        self._pump_event_id = None

    def init(self):
        # BasePlugin notification hooks do not expose these events directly.
        # The plugin loader removes callbacks belonging to this plugin on unload.
        events.connect("file-search-response", self._on_file_search_response)
        events.connect("user-info-response", self._on_user_info_response)

    def _local_username(self):
        return (
            getattr(self.core.users, "login_username", None)
            or self.config.sections["server"].get("login", "")
        )

    def _is_local_user(self, username):
        local_username = self._local_username()
        return bool(local_username and username.casefold() == local_username.casefold())

    def _has_release_marker(self, message):
        marker = str(self.settings.get("release_group_marker", "DASH") or "").strip().casefold()
        if not marker:
            return True

        paths = []
        for field in ("list", "privatelist"):
            file_list = getattr(message, field, None) or []
            for file_info in file_list:
                # Nicotine+ represents search results as tuples:
                # (code, virtual_path, size, ext, attributes).
                if isinstance(file_info, (tuple, list)):
                    if len(file_info) > 1 and isinstance(file_info[1], str):
                        paths.append(file_info[1])
                    elif file_info and isinstance(file_info[0], str):
                        paths.append(file_info[0])
                elif isinstance(file_info, str):
                    paths.append(file_info)

        return any(marker in path.casefold() for path in paths)

    def _on_file_search_response(self, message):
        username = getattr(message, "username", None)
        if not isinstance(username, str) or not username.strip():
            return
        if self._is_local_user(username):
            return
        if not getattr(message, "list", None) and not getattr(message, "privatelist", None):
            return
        if not self._has_release_marker(message):
            return
        if (
            username in self._checked_users
            or username in self._requested_users
            or username in self._queued_users
        ):
            return

        self._profile_queue.append(username)
        self._queued_users.add(username)
        self.log(
            "Search result matched release marker '%s'; queued profile check for %s.",
            (self.settings.get("release_group_marker", "DASH"), username),
        )
        self._schedule_pump()

    def _schedule_pump(self):
        if self._pump_event_id is not None:
            return
        self._pump_event_id = events.schedule(0.1, self._pump_queue)

    def _pump_queue(self):
        self._pump_event_id = None
        max_concurrent = max(1, int(self.settings.get("max_concurrent_profiles", 3)))

        while self._profile_queue and len(self._inflight) < max_concurrent:
            username = self._profile_queue.popleft()
            self._queued_users.discard(username)

            if username in self._checked_users or username in self._requested_users:
                continue
            if self._is_local_user(username):
                continue

            self._requested_users.add(username)
            timeout = max(2, int(self.settings.get("profile_timeout_seconds", 8)))
            timeout_event_id = events.schedule(
                timeout, self._on_profile_timeout, callback_args=(username,)
            )
            self._inflight[username] = timeout_event_id

            try:
                # Use Nicotine+'s built-in User Info service for compatibility
                # with packaged builds whose internal message exports differ.
                user_info = getattr(self.core, "userinfo", None)
                if user_info is None or not hasattr(user_info, "show_user"):
                    raise RuntimeError("This Nicotine+ build does not expose the User Info service")
                user_info.show_user(username, refresh=True, switch_page=False)
                self.log("Requesting profile description from %s.", username)
            except Exception as error:
                self._finish_request(username)
                self.log("Could not request profile for %s: %s", (username, error))

    def _finish_request(self, username):
        timeout_event_id = self._inflight.pop(username, None)
        if timeout_event_id is not None:
            events.cancel_scheduled(timeout_event_id)

    def _on_profile_timeout(self, username):
        if username not in self._inflight:
            return
        self._inflight.pop(username, None)
        self.log("No profile response from %s before timeout; continuing.", username)
        self._schedule_pump()

    def _on_user_info_response(self, message):
        username = getattr(message, "username", None)
        description = getattr(message, "descr", None)
        if not isinstance(username, str) or not username.strip():
            return

        self._finish_request(username)
        self._checked_users.add(username)

        if self._is_local_user(username):
            self._schedule_pump()
            return
        if not isinstance(description, str) or not description:
            self.log("Received an empty profile description from %s.", username)
            self._schedule_pump()
            return

        folded_description = description.casefold()
        matched_keyword = next(
            (
                str(keyword).strip()
                for keyword in self.settings.get("profile_keywords", [])
                if str(keyword).strip() and str(keyword).strip().casefold() in folded_description
            ),
            None,
        )

        if matched_keyword is None:
            self.log("Profile checked: %s did not match the configured SKYLiGHT markers.", username)
            self._schedule_pump()
            return

        network_filter = self.core.network_filter
        actions = []
        if not network_filter.is_user_banned(username):
            network_filter.ban_user(username)
            actions.append("banned")
        if self.settings.get("also_ignore", True) and not network_filter.is_user_ignored(username):
            network_filter.ignore_user(username)
            actions.append("ignored")

        if actions:
            self.log(
                "MATCH: %(username)s profile contains %(keyword)r; automatically %(actions)s.",
                {
                    "username": username,
                    "keyword": matched_keyword,
                    "actions": " and ".join(actions),
                },
            )
        else:
            self.log(
                "MATCH: %s profile contains %r, but the configured ban/ignore actions were already applied.",
                (username, matched_keyword),
            )
        self._schedule_pump()

    def disable(self):
        # Cancel scheduled work. The plugin loader also disconnects its callbacks.
        if self._pump_event_id is not None:
            events.cancel_scheduled(self._pump_event_id)
            self._pump_event_id = None
        for _username, timeout_event_id in list(self._inflight.items()):
            if timeout_event_id is not None:
                events.cancel_scheduled(timeout_event_id)
        self._inflight.clear()
        self._profile_queue.clear()
        self._queued_users.clear()
