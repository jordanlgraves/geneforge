import os
import json
import uuid
import datetime
from typing import List, Dict

from dotenv import load_dotenv

# Ensure environment variables from .env are loaded
load_dotenv()

class ChatHistoryLogger:
    """Utility class that stores the chat history of a single session.

    A unique file is created for every session inside the directory pointed to
    by the ``CHAT_HISTORY_OUT_DIR`` environment variable.  After every message
    update the file is overwritten with the latest list of messages so that the
    on-disk copy always mirrors the in-memory history.
    """

    def __init__(self) -> None:
        out_dir = os.getenv("CHAT_HISTORY_OUT_DIR")
        if not out_dir:
            raise EnvironmentError(
                "Environment variable 'CHAT_HISTORY_OUT_DIR' is not set. "
                "Please define it (e.g. in your .env file) so that chat logs "
                "can be persisted."
            )

        # Lazily create the output directory tree
        os.makedirs(out_dir, exist_ok=True)

        # Generate a unique filename for this session – timestamp + short UUID
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        short_uid = uuid.uuid4().hex[:8]
        self._file_path = os.path.join(out_dir, f"{timestamp}_{short_uid}.json")

        # Internal storage for the message list
        self._history: List[Dict] = []

    # ------------------------------------------------------------------
    #  Public helpers
    # ------------------------------------------------------------------

    def add_message(self, message: Dict) -> None:
        """Append a single message *and* write the file to disk."""
        self._history.append(message)
        self._write()

    def set_history(self, messages: List[Dict]) -> None:
        """Replace the stored history and write to disk."""
        self._history = list(messages)
        self._write()

    def get_history(self) -> List[Dict]:
        """Return an (immutable) copy of the current history."""
        return list(self._history)

    def get_path(self) -> str:
        """Return the absolute path of the JSON file used for this session."""
        return self._file_path

    # ------------------------------------------------------------------
    #  Private helpers
    # ------------------------------------------------------------------

    def _write(self) -> None:
        """Write the in-memory history to *self._file_path* as pretty JSON."""
        try:
            with open(self._file_path, "w", encoding="utf-8") as fp:
                json.dump(self._history, fp, indent=2, ensure_ascii=False)
        except Exception as exc:
            # Import inside function to avoid heavy dependency at import time
            import logging
            logging.getLogger(__name__).error("Failed to write chat history: %s", exc) 