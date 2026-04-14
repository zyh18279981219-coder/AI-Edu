from typing import Any, Dict, Optional
import json
import logging
import os
import secrets
import sys
from datetime import datetime, timedelta
from pathlib import Path

from DatabaseModule.sqlite_store import get_sqlite_store

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    import msvcrt

    def lock_file(f, exclusive=True):
        mode = msvcrt.LK_LOCK if exclusive else msvcrt.LK_NBLCK
        msvcrt.locking(f.fileno(), mode, 1)

    def unlock_file(f):
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
else:
    import fcntl

    def lock_file(f, exclusive=True):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)

    def unlock_file(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class SessionManager:
    def __init__(self):
        self.store = get_sqlite_store()
        self._session_timeout = timedelta(hours=24)
        self._session_dir = Path("data/sessions")
        self._user_state_dir = Path("data/user_state")

    def _get_session_file(self, session_id: str) -> Path:
        return self._session_dir / f"{session_id}.json"

    def _get_user_state_file(self, username: str) -> Path:
        safe_username = str(username).replace("/", "_").replace("\\", "_")
        return self._user_state_dir / f"{safe_username}.json"

    def _get_lock_file(self, file_path: Path) -> Path:
        return file_path.with_suffix(file_path.suffix + ".lock")

    def _salvage_json_text(self, raw_text: str) -> Optional[Dict[str, Any]]:
        content = str(raw_text or "").strip()
        if not content:
            return None
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(content)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            return None
        return None

    def _read_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        if not file_path.exists():
            return None

        lock_path = self._get_lock_file(file_path)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.touch(exist_ok=True)

        try:
            with open(lock_path, "r+", encoding="utf-8") as lock_handle:
                lock_file(lock_handle, exclusive=True)
                try:
                    with open(file_path, "r", encoding="utf-8") as data_handle:
                        raw_text = data_handle.read().lstrip("\ufeff")
                    try:
                        return json.loads(raw_text)
                    except json.JSONDecodeError:
                        salvaged = self._salvage_json_text(raw_text)
                        if salvaged is not None:
                            self._write_json_file(file_path, salvaged)
                            return salvaged
                        return None
                finally:
                    unlock_file(lock_handle)
        except (FileNotFoundError, KeyError, OSError):
            return None

    def _write_json_file(self, file_path: Path, data: Dict[str, Any]):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self._get_lock_file(file_path)
        lock_path.touch(exist_ok=True)
        temp_path = file_path.with_suffix(file_path.suffix + ".tmp")

        with open(lock_path, "r+", encoding="utf-8") as lock_handle:
            lock_file(lock_handle, exclusive=True)
            try:
                with open(temp_path, "w", encoding="utf-8") as temp_handle:
                    json.dump(data, temp_handle, ensure_ascii=False)
                    temp_handle.flush()
                    os.fsync(temp_handle.fileno())
                os.replace(temp_path, file_path)
            finally:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass
                unlock_file(lock_handle)

    def read_json_file(self, file_path: Path | str) -> Optional[Dict[str, Any]]:
        return self._read_json_file(Path(file_path))

    def _read_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            data = self.store.get_session(session_id)
            if data is not None:
                logger.info("SessionManager: read session from SQLite for %s", session_id)
            else:
                return None
        except Exception:
            logger.exception("SessionManager: failed reading session from SQLite for %s", session_id)
            return None

        if not data:
            return None

        try:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])
            data["session_id"] = session_id
            return data
        except (KeyError, ValueError, TypeError):
            return None

    def _write_session(self, session_id: str, data: Dict[str, Any]):
        save_data = data.copy()
        save_data["created_at"] = data["created_at"].isoformat()
        save_data["last_accessed"] = data["last_accessed"].isoformat()
        save_data["session_id"] = session_id
        try:
            self.store.save_session(session_id, save_data)
            logger.info("SessionManager: wrote session SQLite for %s", session_id)
        except Exception:
            logger.exception("SessionManager: failed writing session SQLite for %s", session_id)

    def _read_user_state(self, username: str) -> Dict[str, Any]:
        try:
            state = self.store.get_user_state(username)
            if state is not None:
                logger.info("SessionManager: read user_state from SQLite for %s", username)
                return state
        except Exception:
            logger.exception("SessionManager: failed reading user_state from SQLite for %s", username)
        return {}

    def _write_user_state(self, username: str, data: Dict[str, Any]):
        try:
            self.store.save_user_state(username, data)
            logger.info("SessionManager: wrote user_state SQLite for %s", username)
        except Exception:
            logger.exception("SessionManager: failed writing user_state SQLite for %s", username)

    def create_session(self, username: str, user_type: str, user_data: Dict[str, Any]) -> str:
        session_id = secrets.token_urlsafe(32)
        canonical_username = user_data.get("username") or username
        session_data = {
            "username": canonical_username,
            "user_type": user_type,
            "user_data": user_data,
            "user_id": user_data.get("user_id"),
            "login_id": user_data.get("login_id"),
            "created_at": datetime.now(),
            "last_accessed": datetime.now(),
            "current_pdf_path": None,
            "current_node": None,
        }
        self._write_session(session_id, session_data)
        return session_id

    def set_current_pdf(self, session_id: str, pdf_path: str):
        session = self._read_session(session_id)
        if session:
            session["current_pdf_path"] = pdf_path
            self._write_session(session_id, session)

    def get_current_pdf(self, session_id: str) -> Optional[str]:
        session = self._read_session(session_id)
        if session:
            return session.get("current_pdf_path")
        return None

    def set_current_node(self, session_id: str, node_name: str):
        session = self._read_session(session_id)
        if session:
            session["current_node"] = node_name
            self._write_session(session_id, session)

    def get_current_node(self, session_id: str) -> Optional[str]:
        session = self._read_session(session_id)
        if session:
            return session.get("current_node")
        return None

    def set_value(self, session_id: str, key: str, value: Any):
        session = self._read_session(session_id)
        if session:
            session[key] = value
            self._write_session(session_id, session)

    def get_value(self, session_id: str, key: str, default: Any = None) -> Any:
        session = self._read_session(session_id)
        if session:
            return session.get(key, default)
        return default

    def set_user_value(self, username: str, key: str, value: Any):
        state = self._read_user_state(username)
        state[key] = value
        self._write_user_state(username, state)

    def get_user_value(self, username: str, key: str, default: Any = None) -> Any:
        state = self._read_user_state(username)
        return state.get(key, default)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self._read_session(session_id)
        if not session:
            return None

        if datetime.now() - session["last_accessed"] > self._session_timeout:
            self.delete_session(session_id)
            return None

        session["last_accessed"] = datetime.now()
        self._write_session(session_id, session)
        return session

    def delete_session(self, session_id: str):
        try:
            self.store.delete_session(session_id)
        except Exception:
            pass

    def cleanup_expired_sessions(self):
        try:
            for session in self.store.list_sessions():
                session_id = session.get("session_id")
                if not session_id:
                    continue
                try:
                    last_accessed = datetime.fromisoformat(session["last_accessed"])
                except (KeyError, TypeError, ValueError):
                    continue
                if datetime.now() - last_accessed > self._session_timeout:
                    self.delete_session(session_id)
        except Exception:
            pass


_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    return _session_manager
