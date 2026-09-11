"""Local project catalog and UI transcripts, separate from identity/audit state."""

from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from cain.common import utc_now


class WorkspaceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.documents_root = self.path.parent / "knowledge"
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS projects_user ON projects(user_id);
                CREATE TABLE IF NOT EXISTS project_documents (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    title TEXT NOT NULL, content_hash TEXT NOT NULL, path TEXT NOT NULL,
                    created_at TEXT NOT NULL, UNIQUE(project_id,content_hash)
                );
                CREATE TABLE IF NOT EXISTS ui_sessions (
                    id TEXT NOT NULL, user_id TEXT NOT NULL, project_id TEXT,
                    created_at TEXT NOT NULL, title TEXT NOT NULL DEFAULT 'Nova conversa',
                    PRIMARY KEY(user_id,id)
                );
                CREATE INDEX IF NOT EXISTS sessions_project ON ui_sessions(user_id,project_id);
                CREATE TABLE IF NOT EXISTS ui_turns (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL, session_id TEXT NOT NULL,
                    payload TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id,session_id) REFERENCES ui_sessions(user_id,id)
                );
                CREATE INDEX IF NOT EXISTS turns_session ON ui_turns(user_id,session_id,created_at);
                CREATE TABLE IF NOT EXISTS response_feedback (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL, turn_id TEXT NOT NULL REFERENCES ui_turns(id),
                    reason TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL
                );
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def require_project(self, user_id, project_id):
        if project_id is None:
            return
        with self.connection() as db:
            if not db.execute("SELECT 1 FROM projects WHERE id=? AND user_id=?",
                              (project_id, user_id)).fetchone():
                raise ValueError("Projeto não encontrado para este usuário")

    def projects(self, user_id):
        with self.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT id,name,created_at FROM projects WHERE user_id=? ORDER BY created_at", (user_id,))]

    def create_project(self, user_id, name):
        if not name.strip() or len(name) > 100:
            raise ValueError("Nome do projeto deve ter entre 1 e 100 caracteres")
        record = {"id": str(uuid4()), "name": name.strip(), "created_at": utc_now()}
        with self.connection() as db:
            db.execute("INSERT INTO projects VALUES (?,?,?,?)",
                       (record["id"], user_id, record["name"], record["created_at"]))
        return record

    def documents(self, user_id, project_id):
        self.require_project(user_id, project_id)
        with self.connection() as db:
            rows = [dict(row) for row in db.execute(
                "SELECT id,title,content_hash,path,created_at FROM project_documents "
                "WHERE project_id=? ORDER BY created_at", (project_id,))]
        return [self._document_snapshot(row, project_id)[0] for row in rows]

    def _document_snapshot(self, row, project_id):
        # Reconstruct application-owned paths, including legacy relative-path rows.
        # Never follow a path supplied by a database row to an unrelated file.
        from uuid import UUID
        try:
            if str(UUID(project_id)) != project_id or str(UUID(row["id"])) != row["id"]:
                raise ValueError("Invalid document identity")
            path = self.documents_root / project_id / (row["id"] + ".md")
            if path.resolve(strict=True) != path:
                raise ValueError("Document path redirects outside its stored location")
            with path.open("rb") as handle:
                raw = handle.read(262145)
        except (OSError, ValueError) as exc:
            raise ValueError("Documento indisponível ou com falha de integridade") from exc
        if len(raw) > 262144 or sha256(raw).hexdigest() != row["content_hash"]:
            raise ValueError("Documento com falha de integridade; bytes diferem da versão recebida")
        return {**dict(row), "path": str(path)}, raw.decode("utf-8")

    def document_corpus(self, user_id, project_id):
        self.require_project(user_id, project_id)
        with self.connection() as db:
            rows = db.execute("SELECT * FROM project_documents WHERE project_id=? ORDER BY created_at",
                              (project_id,)).fetchall()
        snapshots = [self._document_snapshot(row, project_id) for row in rows]
        return {record["path"]: text for record, text in snapshots}

    def add_document(self, user_id, project_id, title, content):
        self.require_project(user_id, project_id)
        if project_id is None:
            raise ValueError("Escolha um projeto para adicionar documentos")
        if Path(title).suffix.lower() not in {".txt", ".md", ".rst"}:
            raise ValueError("Use um arquivo .txt, .md ou .rst")
        encoded = content.encode("utf-8")
        if not content.strip() or len(encoded) > 262144:
            raise ValueError("Documento vazio ou maior que 256 KiB")
        digest = sha256(encoded).hexdigest()
        record_id = str(uuid4())
        # Paths are application-generated; a supplied filename is a display label only.
        directory = self.documents_root / project_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (record_id + ".md")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM project_documents WHERE project_id=? AND content_hash=?",
                                  (project_id, digest)).fetchone()
            if existing:
                record, _ = self._document_snapshot(existing, project_id)
                return {**record, "duplicate": True}
            if db.execute("SELECT count(*) FROM project_documents WHERE project_id=?",
                          (project_id,)).fetchone()[0] >= 200:
                raise ValueError("Projeto atingiu o limite de 200 documentos")
            with path.open("xb") as handle:
                handle.write(encoded)
            db.execute("INSERT INTO project_documents VALUES (?,?,?,?,?,?)",
                       (record_id, project_id, title[:200], digest, str(path), utc_now()))
        return next(row for row in self.documents(user_id, project_id) if row["id"] == record_id)

    def ensure_session(self, user_id, session_id, project_id=None):
        self.require_project(user_id, project_id)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM ui_sessions WHERE user_id=? AND id=?",
                             (user_id, session_id)).fetchone()
            if row is not None:
                if row["project_id"] != project_id:
                    raise ValueError("Esta conversa pertence a outro projeto")
                return dict(row)
            db.execute("INSERT INTO ui_sessions(id,user_id,project_id,created_at) VALUES(?,?,?,?)",
                       (session_id, user_id, project_id, utc_now()))
        return {"id": session_id, "project_id": project_id, "title": "Nova conversa"}

    def require_session(self, user_id, session_id, project_id=None):
        """Validate an existing session's owner and project without creating it."""
        self.require_project(user_id, project_id)
        with self.connection() as db:
            row = db.execute("SELECT * FROM ui_sessions WHERE user_id=? AND id=?",
                             (user_id, session_id)).fetchone()
            if row is None or row["project_id"] != project_id:
                raise ValueError("Conversa não encontrada neste projeto")
            return dict(row)

    def sessions(self, user_id, project_id=None):
        self.require_project(user_id, project_id)
        with self.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT id,title,created_at,project_id FROM ui_sessions WHERE user_id=? "
                "AND project_id IS ? ORDER BY created_at DESC LIMIT 100", (user_id, project_id))]

    def record_turn(self, user_id, session_id, payload, result):
        # The orchestrator already used decision_id as the preference address.
        # Use it for UI history and feedback too, including after a page reload.
        turn_id = result.get("decision_id")
        if not isinstance(turn_id, str) or not turn_id.strip():
            raise ValueError("Resposta precisa de decision_id para identificar o turno")
        if result.get("turn_id", turn_id) != turn_id:
            raise ValueError("turn_id precisa corresponder a decision_id")
        result = {**result, "turn_id": turn_id}
        with self.connection() as db:
            db.execute("INSERT INTO ui_turns VALUES(?,?,?,?,?,?)",
                       (turn_id, user_id, session_id, payload,
                        json.dumps(result, ensure_ascii=False), utc_now()))
            db.execute("UPDATE ui_sessions SET title=? WHERE user_id=? AND id=? AND title='Nova conversa'",
                       (payload[:70], user_id, session_id))
        return turn_id

    def turns(self, user_id, session_id, project_id=None):
        # Read paths never create a session or move one to a different project.
        self.require_session(user_id, session_id, project_id)
        with self.connection() as db:
            rows = db.execute("SELECT * FROM (SELECT * FROM ui_turns WHERE user_id=? AND session_id=? "
                              "ORDER BY created_at DESC LIMIT 100) ORDER BY created_at",
                              (user_id, session_id)).fetchall()
        return [{"id": row["id"], "payload": row["payload"], "result": json.loads(row["result_json"]),
                 "created_at": row["created_at"]} for row in rows]

    def feedback(self, user_id, turn_id, reason, note):
        if reason not in {"useful", "incorrect", "format", "source", "memory", "long"}:
            raise ValueError("Motivo de avaliação inválido")
        if len(note) > 2000:
            raise ValueError("Comentário muito longo")
        record_id = str(uuid4())
        with self.connection() as db:
            if not db.execute("SELECT 1 FROM ui_turns WHERE id=? AND user_id=?", (turn_id, user_id)).fetchone():
                raise ValueError("Resposta não encontrada para este usuário")
            db.execute("INSERT INTO response_feedback VALUES(?,?,?,?,?,?)",
                       (record_id, user_id, turn_id, reason, note, utc_now()))
        return {"id": record_id, "saved": True}
