"""Small UI catalogs and OS display-language selection without global locale changes."""

from __future__ import annotations

import locale
import os

MESSAGES = {
    "help_conversation": ("Conversation and tasks", "Sohbet ve görevler"),
    "skills_used": ("Skills in context: {names}", "Bağlama alınan skill'ler: {names}"),
    "skills_none": (
        "No relevant skill selected; answer directly.",
        "İlgili skill seçilmedi; doğrudan yanıt.",
    ),
    "help_connections": ("Connections and models", "Bağlantılar ve modeller"),
    "help_evidence": ("Changes and verification", "Değişiklikler ve doğrulama"),
    "help_display": ("Display and keyboard", "Görünüm ve klavye"),
    "status_title": ("Session status", "Oturum durumu"),
    "no_project": ("No project selected · general conversation", "Proje seçilmedi · genel sohbet"),
    "mode_label": ("Mode", "Mod"),
    "session_label": ("Session", "Oturum"),
    "status_label": ("Status", "Durum"),
    "settings_title": ("Settings", "Ayarlar"),
    "settings_example": (
        "Change: /settings api_budget_usd 5",
        "Değiştir: /settings api_budget_usd 5",
    ),
    "model_selected": ("Model: {value}", "Model: {value}"),
    "usage_title": ("Observed usage", "Gözlenen kullanım"),
    "no_usage": ("No usage recorded for this task.", "Bu görev için kullanım kaydı yok."),
    "invoice_note": (
        "API estimate; CLI quota is separate. Not the final invoice.",
        "API tahmini; CLI kotası ayrıdır. Kesin fatura değildir.",
    ),
    "tests_title": ("Observed checks", "Gözlenen kontroller"),
    "no_changes": (
        "No file changes recorded for this task.",
        "Bu görev için dosya değişikliği kaydedilmedi.",
    ),
    "check_passed": ("PASS", "GEÇTİ"),
    "check_failed": ("FAILED / INCOMPLETE", "BAŞARISIZ / EKSİK"),
    "no_tests": (
        "No checks observed. This task is unverified.",
        "Kontrol çalıştırılmadı. Görev doğrulanmış değildir.",
    ),
    "sessions_title": ("Saved sessions", "Kayıtlı oturumlar"),
    "no_sessions": ("No sessions saved in this scope.", "Bu kapsamda kayıtlı oturum yok."),
    "plan_title": ("Task plan", "Görev planı"),
    "not_started": ("Plan only; execution has not started.", "Yalnızca plan; yürütme başlamadı."),
    "native_policy": (
        "Native CLI settings/plugins keep their own policy.",
        "Native CLI ayar/eklentileri kendi politikasını korur.",
    ),
    "access_note": ("Model access: {value}", "Model erişimi: {value}"),
    "unavailable": ("Unavailable", "Erişilemiyor"),
    "unknown_price": ("Price unknown", "Fiyat bilinmiyor"),
    "no_connections": (
        "Add a connection: /connect codex or /connect openai",
        "Bağlantı ekle: /connect codex veya /connect openai",
    ),
    "cleared": (
        "Visible transcript cleared; session records remain.\n",
        "Görünür konuşma temizlendi; oturum kayıtları korundu.\n",
    ),
    "view_changed": ("View: {view}\n", "Görünüm: {view}\n"),
    "motion_changed": ("Logo motion: {value}\n", "Logo hareketi: {value}\n"),
    "keys_short": (
        "Ctrl+W erase word · Ctrl+U clear · Ctrl+J newline · /help",
        "Ctrl+W kelime sil · Ctrl+U temizle · Ctrl+J yeni satır · /help",
    ),
    "running": ("Running", "Çalışıyor"),
    "completed": ("Completed", "Tamamlandı"),
    "needs_attention": ("Needs attention", "İnceleme gerekiyor"),
    "cancelled": ("Cancelled", "İptal edildi"),
    "implemented_unverified": ("Implemented, unverified", "Uygulandı, doğrulanmadı"),
    "waiting_budget": ("Waiting for budget", "Bütçe bekleniyor"),
    "quote_error": ("Unclosed quote in command", "Komutta kapanmamış tırnak var"),
    "path_required": (
        "/project PATH · Enter your project folder path",
        "/project PATH · Proje klasörünün yolunu yaz",
    ),
    "home_overlap": (
        "This folder contains EROL settings/memory; select a project subfolder",
        "Bu klasör EROL ayar/hafıza klasörünü içeriyor; proje alt klasörünü seç",
    ),
    "ready": ("Ready", "Hazır"),
    "project_required": (
        "This command needs project files. Select /project PATH.",
        "Bu komut proje dosyalarıyla çalışır. /project PATH ile klasör seç.",
    ),
    "general_header": (
        "EROL · General conversation · No project selected\nAPI task budget ${budget:g}\n"
        "/connect · /providers · /models · /language · /research · /project PATH\n"
        "No project files/context are sent. Native CLI settings/plugins retain their own policy.\n",
        "EROL · Genel sohbet · Proje seçilmedi\nAPI görev bütçesi ${budget:g}\n"
        "/connect · /providers · /models · /language · /research · /project PATH\n"
        "Proje dosyaları/bağlamı gönderilmez. "
        "Native CLI ayar/eklentileri kendi politikasını korur.\n",
    ),
    "general_mode": (
        "Projectless mode: {mode} · /project PATH for file tasks\n",
        "Projesiz mod: {mode} · Dosya görevleri için /project PATH\n",
    ),
    "working": ("working", "çalışıyor"),
    "done": ("completed", "tamamlandı"),
    "error": ("Error", "Hata"),
    "ready_hint": (
        "Ready · /help · Enter send · Ctrl+J newline · PgUp/PgDn scroll",
        "Hazır · /help · Enter gönder · Ctrl+J yeni satır · PgUp/PgDn kaydır",
    ),
    "history_hint": (" · PgUp/PgDn history", " · PgUp/PgDn geçmiş"),
    "keys": (
        "Enter send; Ctrl+J newline; Tab complete; Ctrl+C cancel; Backspace/Delete erase; "
        "Ctrl+U clear input; Ctrl+W erase word; Ctrl+K erase to line end; "
        "mouse wheel or PgUp/PgDn scroll; Shift+click select text",
        "Enter gönder; Ctrl+J yeni satır; Tab tamamla; Ctrl+C iptal; Backspace/Delete sil; "
        "Ctrl+U girişi temizle; Ctrl+W kelime sil; Ctrl+K satır sonuna kadar sil; "
        "fare tekerleği veya PgUp/PgDn kaydır; Shift+tık metin seç",
    ),
    "picker_hint": (
        "Select project · /project PATH · /language · /help · /exit",
        "Proje seç · /project PATH · /language · /help · /exit",
    ),
    "picker": (
        "EROL · No project selected\n{base}\nThis folder contains EROL settings and memory. "
        'Select your project folder.\n/project PATH · Example: /project "OneDrive/Desktop/EROL"\n',
        "EROL · Proje seçilmedi\n{base}\nBu klasör EROL ayar ve hafızasını içeriyor. "
        "Çalışacağın proje klasörünü seç.\n/project PATH · Örnek: "
        '/project "OneDrive/Masaüstü/EROL"\n',
    ),
    "picker_help": (
        "/project PATH · Select project\n/logo · Show logo\n/language auto|en|tr · UI language\n"
        "/exit · Exit\nOther commands become available after project selection.\n",
        "/project PATH · Proje seç\n/logo · Logoyu göster\n/language auto|en|tr · Arayüz dili\n"
        "/exit · Çık\nDiğer komutlar proje seçildikten sonra açılır.\n",
    ),
    "choose_first": (
        "First select your project with /project PATH.\n",
        "Önce /project PATH ile çalışacağın proje klasörünü seç.\n",
    ),
    "project_error": (
        "Project path unavailable or contains EROL settings/memory. Select another folder.\n",
        "Proje yolu kullanılamıyor veya EROL ayar/hafıza klasörünü içeriyor. "
        "Başka bir proje klasörü seç.\n",
    ),
    "header": (
        "EROL · {name}\n{root}\nQuality / cost balance · API task budget ${budget:g}\n"
        "/help commands · /connect connections · /language auto|en|tr\n",
        "EROL · {name}\n{root}\nKalite / maliyet dengesi · API görev bütçesi ${budget:g}\n"
        "/help komutlar · /connect bağlantılar · /language auto|en|tr\n",
    ),
    "language": (
        "UI language: {language} (setting: {preference})\n",
        "Arayüz dili: {language} (ayar: {preference})\n",
    ),
    "language_invalid": ("Use /language auto|en|tr", "/language auto|en|tr kullan"),
    "logo_size": (
        "Expand the terminal to at least 72 columns and 18 rows for the logo panel.\n",
        "Logo alanı için terminali en az 72 sütun ve 18 satıra genişlet.\n",
    ),
    "cancel": ("Cancelling; stopping processes", "İptal ediliyor; süreçler kapanıyor"),
    "stopped": (
        "\nTask stopped; inspect changes with /diff.\n",
        "\nGörev durduruldu; değişiklikler /diff ile görülebilir.\n",
    ),
    "invalid": (
        "Invalid command or unavailable resource",
        "Geçersiz komut veya kullanılamayan kaynak",
    ),
    "unknown": ("Unknown command; use /help", "Bilinmeyen komut; /help yaz"),
    "task_required": ("Describe a task or use /help.\n", "Bir görev yaz veya /help kullan.\n"),
    "accounted": ("API accounted", "API hesabı"),
    "estimate": ("estimated", "tahmini"),
    "project_changed": (
        "Project: {root}\nNew session: {session}\n",
        "Proje: {root}\nYeni oturum: {session}\n",
    ),
    "previous": ("Previous step {task_id}:\n", "Önceki adım {task_id}:\n"),
    "connected": (
        "Connection registered: {id} ({kind}); {count} model profiles.\n"
        "Use /providers to check login/access; /models lists profiles.\n",
        "Bağlantı kaydedildi: {id} ({kind}); {count} model profili.\n"
        "Giriş/erişim kontrolü: /providers; model profilleri: /models.\n",
    ),
}

HELP_EN = {
    "help": "Show commands and examples",
    "project": "Show/select project: /project C:/Projects/my-app (quote spaces)",
    "general": "Switch to projectless conversation: /general [MESSAGE]",
    "research": "Projectless source research: /research [QUESTION or URL]",
    "connect": "Add CLI/API: /connect codex | /connect openai work OPENAI_API_KEY",
    "providers": "Check connection login/capabilities; /providers disable ID",
    "models": "Model profiles; /models refresh | /models add ID JSON_PROFILE",
    "model": "Automatic or manual: /model auto | /model CONNECTION:MODEL",
    "settings": "Show/change settings: /settings api_budget_usd 5",
    "plan": "Plan without execution: /plan TASK",
    "diff": "Latest task's added/modified/deleted files and diffs",
    "tests": "Latest test results observed by EROL",
    "usage": "Token events and task API budget; not the final bill",
    "status": "Project, session and latest task status",
    "new": "Start a new session",
    "resume": "List/load sessions: /resume ID | /resume ID continue",
    "logo": "Expand/shrink the right logo; static in plain terminals",
    "language": "UI language: /language auto | /language en | /language tr",
    "clear": "Clear visible transcript; session records and files remain",
    "view": "Layout: /view compact (wide response) | /view full (logo panel)",
    "motion": "Logo motion: /motion on | /motion off",
    "exit": "Exit the terminal",
}


def os_language() -> str:
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            function = ctypes.WinDLL("kernel32").GetUserDefaultUILanguage  # type: ignore[attr-defined]
            function.argtypes, function.restype = [], wintypes.WORD
            language_id = function()
            if language_id:
                return "tr" if language_id & 0x3FF == 0x1F else "en"
        except (AttributeError, OSError):
            pass
    value = next(
        (os.environ[k] for k in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG") if os.environ.get(k)),
        "",
    )
    if not value:
        try:
            value = locale.getlocale()[0] or ""
        except ValueError:
            value = ""
    return "tr" if value.lower().replace("-", "_").split("_")[0].split(":")[0] == "tr" else "en"


def resolve_language(preference: str) -> str:
    return os_language() if preference == "auto" else preference


def message(locale_name: str, key: str, **values) -> str:
    return MESSAGES[key][1 if locale_name == "tr" else 0].format(**values)
