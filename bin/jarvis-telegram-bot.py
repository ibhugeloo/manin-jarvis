#!/usr/bin/env python3
"""
jarvis-telegram-bot — Bridge Telegram ↔ Claude Code (jarvis).

Long-polling bot : reçoit les messages du boss, les passe à `claude -p` avec
contexte conversationnel, renvoie la réponse. Tourne en boucle, lancé par launchd.
"""

from __future__ import annotations  # type hints en string → compat Python 3.9 (macOS natif)

import json
import os
import shlex
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HOME = Path.home()
ENV_FILE = HOME / ".config" / "jarvis" / "telegram.env"
HISTORY_FILE = HOME / ".local" / "share" / "jarvis" / "telegram-history.jsonl"
LOG_FILE = HOME / ".local" / "var" / "log" / "jarvis-telegram-bot.log"
SYSTEM_PROMPT_FILE = HOME / ".local" / "share" / "jarvis" / "telegram-system-prompt.md"
OFFSET_FILE = HOME / ".local" / "share" / "jarvis" / "telegram-last-offset.txt"
CLAUDE_BIN = HOME / ".local" / "bin" / "claude"
LOCAL_BIN = HOME / ".local" / "bin"

MAX_HISTORY_TURNS = 5  # nombre de paires user+jarvis gardées en contexte
MAX_TG_MSG_LEN = 4000
POLL_TIMEOUT = 30  # long-polling Telegram
HTTP_TIMEOUT = 60

# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")


def load_env() -> dict:
    if not ENV_FILE.exists():
        log(f"Config absente : {ENV_FILE}. Lancer jarvis-telegram-setup, puis 'launchctl kickstart -k gui/$UID/com.example.jarvis.telegram-bot'.")
        # Exit 0 pour éviter que launchd ne respawn en boucle (KeepAlive SuccessfulExit:false)
        sys.exit(0)
    cfg = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    if "BOT_TOKEN" not in cfg or "CHAT_ID" not in cfg:
        sys.exit(f"❌ BOT_TOKEN ou CHAT_ID manquant dans {ENV_FILE}")
    return cfg


def tg_request(token: str, method: str, params: dict | None = None, timeout: int = HTTP_TIMEOUT) -> dict:
    """Appel API Telegram. Retourne le JSON ou {} en cas d'erreur."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params or {}).encode() if params else None
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log(f"tg_request {method} ERROR: {e}")
        return {}


def tg_send(token: str, chat_id: str, text: str, parse_mode: str | None = None) -> bool:
    """Envoie un message, en chunkant si > 4000 chars."""
    chunks = [text[i : i + MAX_TG_MSG_LEN] for i in range(0, len(text), MAX_TG_MSG_LEN)] or [""]
    for chunk in chunks:
        params = {"chat_id": chat_id, "text": chunk}
        if parse_mode:
            params["parse_mode"] = parse_mode
        resp = tg_request(token, "sendMessage", params)
        if not resp.get("ok"):
            log(f"sendMessage failed: {resp}")
            return False
    return True


def tg_send_typing(token: str, chat_id: str) -> None:
    """Envoie l'action 'typing...' pour indiquer qu'on traite (persist ~5s côté Telegram)."""
    tg_request(token, "sendChatAction", {"chat_id": chat_id, "action": "typing"}, timeout=5)


def tg_send_ack(token: str, chat_id: str, model: str) -> int | None:
    """Envoie un message d'accusé de réception, retourne le message_id pour édition ultérieure."""
    emoji = "⚡" if model == "haiku" else "🧠"
    estimate = "~10s" if model == "haiku" else "~30s à 3min"
    text = f"{emoji} _{model} · {estimate}_"
    resp = tg_request(token, "sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    if resp.get("ok"):
        return resp["result"]["message_id"]
    return None


def tg_edit_message(token: str, chat_id: str, message_id: int, text: str) -> bool:
    """Édite un message existant. Retourne False si édition impossible (msg trop long, etc.)."""
    if len(text) > MAX_TG_MSG_LEN:
        return False
    resp = tg_request(token, "editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    })
    return bool(resp.get("ok"))


def tg_delete_message(token: str, chat_id: str, message_id: int) -> None:
    """Supprime un message (utilisé pour nettoyer l'accusé si la réponse est trop longue à éditer)."""
    tg_request(token, "deleteMessage", {"chat_id": chat_id, "message_id": message_id})


def tg_download_photo(token: str, file_id: str) -> str | None:
    """Télécharge une photo Telegram en local. Retourne le chemin du fichier ou None."""
    info = tg_request(token, "getFile", {"file_id": file_id})
    if not info.get("ok"):
        log(f"getFile failed: {info}")
        return None
    file_path = info["result"].get("file_path")
    if not file_path:
        return None
    url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    ext = Path(file_path).suffix or ".jpg"
    local_path = Path("/tmp") / f"jarvis-photo-{file_id[-12:]}{ext}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            local_path.write_bytes(resp.read())
        return str(local_path)
    except Exception as e:
        log(f"download photo ERROR: {e}")
        return None


class TypingKeeper:
    """Garde l'indicateur 'typing...' actif pendant le traitement (refresh toutes les 4s)."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        def loop():
            while not self.stop_event.is_set():
                tg_send_typing(self.token, self.chat_id)
                # tg_send_typing persiste ~5s côté client → refresh toutes les 4s
                self.stop_event.wait(4)

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)


def load_history() -> list[dict]:
    """Charge les N derniers tours de conversation."""
    if not HISTORY_FILE.exists():
        return []
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = HISTORY_FILE.read_text().splitlines()
    turns = [json.loads(line) for line in lines if line.strip()]
    return turns[-MAX_HISTORY_TURNS * 2 :]


def append_history(role: str, content: str) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps({"role": role, "content": content, "ts": datetime.now().isoformat()}) + "\n")


def clear_history() -> None:
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()


def load_last_offset() -> int:
    """Charge le dernier update_id confirmé pour reprise après crash/restart."""
    if not OFFSET_FILE.exists():
        return 0
    try:
        return int(OFFSET_FILE.read_text().strip())
    except Exception:
        return 0


def save_last_offset(update_id: int) -> None:
    """Sauve le update_id à utiliser comme offset au prochain appel getUpdates."""
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(update_id))


def load_system_prompt() -> str:
    if not SYSTEM_PROMPT_FILE.exists():
        return "Tu es Jarvis, le majordome du boss. Réponds en français, vouvoiement, court et précis."
    return SYSTEM_PROMPT_FILE.read_text()


HAIKU_KEYWORDS = (
    "heure", "quand", "quand est", "c'est quoi", "c'est qui", "où est", "où sont",
    "quel est", "quelle est", "combien", "rappelle", "rdv", "rendez-vous", "météo",
    "aujourd'hui", "demain", "matin", "soir", "semaine", "status", "brief",
    "en est", "reste", "top", "liste", "donne-moi", "c'est quand",
)

SONNET_KEYWORDS = (
    "analyse", "explique", "compare", "stratégie", "plan", "synthèse",
    "rédige", "écris", "crée", "créer", "génère", "propose", "code",
    "draft", "mail", "email", "notion", "page", "mémoire", "bilan",
    "rapport", "optimise", "restructure", "refactor", "migration",
)


def route_model(user_msg: str) -> str:
    """Choisit le modèle selon la complexité estimée du message."""
    msg = user_msg.lower()
    # Forcer Sonnet si keyword complexe détecté
    for kw in SONNET_KEYWORDS:
        if kw in msg:
            return "sonnet"
    # Forcer Haiku si message court OU keyword simple détecté
    if len(user_msg) < 80:
        return "haiku"
    for kw in HAIKU_KEYWORDS:
        if kw in msg:
            return "haiku"
    # Par défaut : Sonnet pour les longs messages sans signal clair
    return "sonnet"


def call_claude(user_msg: str, model: str) -> str:
    """Appelle claude -p avec le contexte conversationnel et retourne la réponse."""
    system = load_system_prompt()
    history = load_history()

    # Construction du prompt avec contexte
    history_str = ""
    for turn in history:
        role = "le boss" if turn["role"] == "user" else "Vous (Jarvis)"
        history_str += f"\n## {role}\n{turn['content']}\n"

    full_prompt = f"""{system}

# Contexte de la conversation
{history_str if history_str else "_(début de conversation)_"}

# Nouveau message du boss
{user_msg}

# Instruction
Réponds directement en tant que Jarvis. Pas de préambule, pas de signature."""

    try:
        result = subprocess.run(
            [
                str(CLAUDE_BIN),
                "--print",
                "--model", model,
                "--dangerously-skip-permissions",
                "--output-format", "text",
            ],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "JARVIS_TELEGRAM_BOT": "1"},
        )
        if result.returncode != 0:
            log(f"claude exit={result.returncode} stderr={result.stderr[:500]}")
            return f"❌ Erreur Claude (exit {result.returncode}). Voir logs."
        return result.stdout.strip() or "(_réponse vide_)"
    except subprocess.TimeoutExpired:
        log("claude TIMEOUT")
        return "❌ Délai dépassé (>3 min)."
    except Exception as e:
        log(f"claude EXCEPTION: {e}")
        return f"❌ Erreur : {e}"


def handle_command(token: str, chat_id: str, cmd: str, args: str) -> str | None:
    """Commandes courtes qui bypass Claude. Return None si commande inconnue."""
    cmd = cmd.lower()

    if cmd == "/start" or cmd == "/help":
        return (
            "Bonjour, boss. Voici les commandes disponibles :\n\n"
            "/status — état des repos GIT PROD\n"
            "/brief — brief matinal du jour\n"
            "/soir — récap soir du jour\n"
            "/clear — efface l'historique de cette conversation\n"
            "/help — cette aide\n\n"
            "Pour le reste, parlez-moi naturellement."
        )

    if cmd == "/clear":
        clear_history()
        return "🧹 Historique effacé. On repart à zéro."

    if cmd == "/status":
        try:
            r = subprocess.run([str(LOCAL_BIN / "jarvis-status")], capture_output=True, text=True, timeout=10)
            return f"```\n{r.stdout}\n```" if r.stdout else "(_aucun repo_)"
        except Exception as e:
            return f"❌ {e}"

    if cmd == "/brief":
        today = datetime.now().strftime("%Y-%m-%d")
        f = HOME / "Documents" / "Obsidian" / "vault" / "Brief" / f"{today}.md"
        if f.exists():
            return f.read_text()
        return f"_Brief du {today} pas encore généré._"

    if cmd == "/soir":
        today = datetime.now().strftime("%Y-%m-%d")
        f = HOME / "Documents" / "Obsidian" / "vault" / "Brief" / f"{today}-soir.md"
        if f.exists():
            return f.read_text()
        return f"_Récap soir du {today} pas encore généré._"

    return None


def process_update(token: str, chat_id: str, message: dict) -> None:
    """Traite un message reçu."""
    sender_id = str(message.get("from", {}).get("id", ""))
    if sender_id != chat_id:
        log(f"Message ignoré (sender={sender_id} ≠ authorized {chat_id})")
        return

    # Détection photo : Telegram fournit `photo` (liste de tailles, prendre la dernière = plus grande)
    photo_path: str | None = None
    if message.get("photo"):
        sizes = message["photo"]
        # Trier par dimensions, prendre la plus grande
        sizes_sorted = sorted(sizes, key=lambda s: s.get("width", 0) * s.get("height", 0), reverse=True)
        biggest = sizes_sorted[0]
        log(f"PHOTO RECV: {biggest.get('width')}x{biggest.get('height')} file_id={biggest.get('file_id', '')[:20]}...")
        photo_path = tg_download_photo(token, biggest["file_id"])
        if photo_path:
            log(f"Photo dl OK: {photo_path}")
        else:
            tg_send(token, chat_id, "❌ Échec du téléchargement de la photo.")
            return

    caption = (message.get("caption") or "").strip()
    text = (message.get("text") or "").strip()

    # Sticker / vocal / autre non géré
    if not photo_path and not text:
        tg_send(token, chat_id, "_Type de message non géré pour l'instant. J'accepte texte et photos._")
        return

    log(f"RECV: {('[photo] ' if photo_path else '')}{(text or caption)[:200]}")

    # Commandes (uniquement si pas de photo)
    if text and text.startswith("/") and not photo_path:
        parts = text.split(" ", 1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        response = handle_command(token, chat_id, cmd, args)
        if response is not None:
            tg_send(token, chat_id, response, parse_mode="Markdown" if "```" in response else None)
            return

    # Construire le message effectif pour Claude
    if photo_path:
        # Image en multimodal : @<path> indique à Claude Code de la charger
        instruction = caption or "Analysez ou décrivez cette image selon le contexte."
        user_msg_for_claude = f"@{photo_path}\n\n{instruction}"
        text = caption or "[photo sans texte]"  # pour l'historique et le routing
    else:
        user_msg_for_claude = text

    # Message → Claude
    # 1. Routing modèle : photos forcent sonnet (vision plus solide), sinon heuristique
    if photo_path:
        model = "sonnet"
        log(f"MODEL_ROUTE: sonnet (photo détectée)")
    else:
        model = route_model(text)
        log(f"MODEL_ROUTE: {model} for msg={text[:60]!r}")

    # 2. Accusé de réception immédiat (le boss voit que le bot a reçu)
    ack_id = tg_send_ack(token, chat_id, model)

    # 3. Garder l'indicateur "typing..." actif tant que claude tourne
    typing = TypingKeeper(token, chat_id)
    typing.start()

    # 4. Appel claude
    started = time.time()
    append_history("user", text + (" [photo jointe]" if photo_path else ""))
    try:
        response = call_claude(user_msg_for_claude, model)
    finally:
        typing.stop()
        # Cleanup de la photo temporaire
        if photo_path:
            try:
                Path(photo_path).unlink(missing_ok=True)
            except Exception:
                pass
    elapsed = time.time() - started
    append_history("assistant", response)

    # 5. Envoyer la réponse — éditer l'accusé si possible (msg court), sinon nouveau msg
    if ack_id is not None and len(response) <= MAX_TG_MSG_LEN:
        if not tg_edit_message(token, chat_id, ack_id, response):
            tg_send(token, chat_id, response)
    else:
        if ack_id is not None:
            tg_delete_message(token, chat_id, ack_id)
        tg_send(token, chat_id, response)

    log(f"SENT ({model}, {elapsed:.1f}s): {response[:200]}")


def main() -> None:
    cfg = load_env()
    token = cfg["BOT_TOKEN"]
    chat_id = str(cfg["CHAT_ID"])

    log(f"Bot started. Authorized chat_id={chat_id}, bot=@{cfg.get('BOT_USERNAME', '?')}")

    # Reprise après crash : on lit le dernier offset confirmé sur disque.
    # Si premier démarrage (pas de fichier) → drain pour éviter de traiter d'anciens messages.
    last_offset = load_last_offset()
    if last_offset == 0:
        # Premier run — drain les updates en attente
        init = tg_request(token, "getUpdates", {"timeout": "0", "offset": "-1"})
        if init.get("ok") and init.get("result"):
            last_offset = init["result"][-1]["update_id"] + 1
            save_last_offset(last_offset)
        log(f"First run, drained. Starting from offset {last_offset}")
    else:
        log(f"Resume from saved offset {last_offset}")

    while True:
        try:
            resp = tg_request(
                token,
                "getUpdates",
                {"timeout": str(POLL_TIMEOUT), "offset": str(last_offset)},
                timeout=POLL_TIMEOUT + 10,
            )
            if not resp.get("ok"):
                log(f"getUpdates failed, sleeping 10s. Resp: {resp}")
                time.sleep(10)
                continue

            for update in resp.get("result", []):
                update_id = update["update_id"]
                if "message" in update:
                    try:
                        process_update(token, chat_id, update["message"])
                    except Exception as e:
                        log(f"process_update EXCEPTION: {e}")
                        try:
                            tg_send(token, chat_id, f"❌ Erreur interne : {e}")
                        except Exception:
                            pass
                # Acker l'update SEULEMENT après traitement (succès ou exception caught)
                # → en cas de crash mid-processing, on retentera sur restart
                last_offset = update_id + 1
                save_last_offset(last_offset)
        except KeyboardInterrupt:
            log("Stopping (KeyboardInterrupt)")
            break
        except Exception as e:
            log(f"main loop EXCEPTION: {e}, sleeping 5s")
            time.sleep(5)


if __name__ == "__main__":
    main()
