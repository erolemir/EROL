"""Small UI catalogs and OS display-language selection without global locale changes."""

from __future__ import annotations

import locale
import os

MESSAGES = {
    "menu_exit": ("Exit EROL", "EROL'dan çık"),
    "menu_start": ("Set up / choose a connection", "Başlangıç / bağlantı seç"),
    "menu_folder": ("Open a project folder", "Proje klasörü aç"),
    "menu_new": ("Start a new chat", "Yeni sohbet başlat"),
    "menu_rename": ("Name this chat", "Bu sohbete isim ver"),
    "menu_language": ("Choose interface language", "Arayüz dilini seç"),
    "menu_general": ("General conversation", "Genel sohbet"),
    "menu_research": ("Research with sources", "Kaynaklı araştırma"),
    "connection_cli": ("CLI · install and log in first", "CLI · önce kur ve giriş yap"),
    "connection_api": (
        "API · uses an environment variable; /providers checks access",
        "API · ortam değişkenini kullanır; /providers erişimi kontrol eder",
    ),
    "connection_custom": (
        "Custom API: /connect compatible ID KEY_ENV HTTPS_URL",
        "Özel API: /connect compatible ID KEY_ENV HTTPS_URL",
    ),
    "setup_ready": (
        "Connection saved. /providers checks access; /model chooses a model. "
        "Describe your task next.\n",
        "Bağlantı kaydedildi. /providers erişimi kontrol eder; /model ile model seçebilirsin. "
        "Ardından görevini yaz.\n",
    ),
    "folder_prompt": (
        "Paste the project folder path (blank or Esc to cancel):\n",
        "Proje klasörünün yolunu yapıştır (iptal için boş bırak veya Esc):\n",
    ),
    "rename_prompt": (
        "Type a name for this chat (blank or Esc to cancel):\n",
        "Bu sohbete isim yaz (iptal için boş bırak veya Esc):\n",
    ),
    "draft_kept": (
        "Connection setup cancelled. Your task is kept; connect and send it again.\n",
        "Bağlantı seçimi iptal edildi. Görevin korundu; bağlantı kurup tekrar gönder.\n",
    ),
    "no_matches": (
        "No matches · Backspace to change search",
        "Eşleşme yok · aramayı değiştirmek için Backspace",
    ),
    "menu_title": ("What would you like to do?", "Ne yapmak istiyorsun?"),
    "menu_projects": ("Choose a project", "Proje seç"),
    "menu_models": ("Choose a model", "Model seç"),
    "menu_effort": ("Choose reasoning effort", "Düşünme eforunu seç"),
    "next_page": ("Next page", "Sonraki sayfa"),
    "previous_page": ("Previous page", "Önceki sayfa"),
    "menu_chats": ("Open a saved chat", "Eski sohbeti aç"),
    "menu_files": ("Find output files", "Üretilen dosyaları bul"),
    "menu_changes": ("See file changes", "Dosya değişikliklerini gör"),
    "menu_tests": ("See test results", "Test sonuçlarını gör"),
    "menu_status": ("See project and task status", "Proje ve görev durumunu gör"),
    "menu_view": ("Switch reading layout", "Okuma görünümünü değiştir"),
    "menu_settings": ("See settings", "Ayarları gör"),
    "menu_help": ("All commands and examples", "Tüm komutlar ve örnekler"),
    "choice_hint": (
        "Type to search · ↑/↓ choose · Enter open · Esc back",
        "Yazarak ara · ↑/↓ seç · Enter aç · Esc geri",
    ),
    "choice_plain": (
        "Number or search (blank to go back): ",
        "Numara veya arama (geri dönmek için boş bırak): ",
    ),
    "auto_model": ("Automatic · choose for each task", "Otomatik · göreve göre seç"),
    "welcome_actions": (
        "\nDescribe your task. Press Enter for the menu; /start for setup.\n"
        "/my-projects  project · /model  model · /chats  saved chats\n"
        "/files  output paths · /diff  changes · /tests  checks\n",
        "\nGörevini yaz. Menü için Enter; başlangıç için /start.\n"
        "/my-projects  proje · /model  model · /chats  eski sohbetler\n"
        "/files  çıktı yolları · /diff  değişiklikler · /tests  kontroller\n",
    ),
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
    "token_counts": (
        "tokens in {input} / out {output} / total {total}",
        "token giriş {input} / çıkış {output} / toplam {total}",
    ),
    "cli_quota_unknown": ("CLI quota unknown", "CLI kotası bilinmiyor"),
    "cli_subscription": ("CLI subscription · token usage", "CLI aboneliği · token kullanımı"),
    "api_budget": ("API task budget ${budget:g}", "API görev bütçesi ${budget:g}"),
    "unreported_reservation": (
        "unreported token usage · reserved estimate ${amount:.4f}",
        "token kullanımı bildirilmedi · ayrılan tahmin ${amount:.4f}",
    ),
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
    "projects_title": ("My projects", "Projelerim"),
    "no_projects": (
        "No saved projects. Add one with /my-projects add PATH.",
        "Kayıtlı proje yok. /my-projects add PATH ile ekle.",
    ),
    "projects_hint": (
        "Select: /my-projects NUMBER · Add: /my-projects add PATH",
        "Seç: /my-projects NUMARA · Ekle: /my-projects add PATH",
    ),
    "missing_project": ("Folder unavailable", "Klasör erişilemiyor"),
    "chat_title": ("Chat: {title}", "Sohbet: {title}"),
    "chats_hint": (
        "Open: /chats NUMBER · Details: /chats show NUMBER · "
        "Rename: /chats rename NUMBER TITLE · More: /chats page {next}",
        "Aç: /chats NUMARA · Ayrıntı: /chats show NUMARA · "
        "İsim: /chats rename NUMARA İSİM · Devamı: /chats page {next}",
    ),
    "saved_chat_note": (
        "Saved summary, changes and checks; full message transcript was not retained.",
        "Kayıtlı özet, değişiklik ve kontroller; tam mesaj geçmişi saklanmadı.",
    ),
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
        "/menu actions · Tab complete/cycle · Ctrl+J newline · PgUp/PgDn scroll",
        "/menu eylemler · Tab tamamla/geç · Ctrl+J yeni satır · PgUp/PgDn kaydır",
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
        "EROL · General conversation · No project selected\n{resources}\n"
        "/connect · /providers · /models · /language · /research · /project PATH\n"
        "No project files/context are sent. Native CLI settings/plugins retain their own policy.\n",
        "EROL · Genel sohbet · Proje seçilmedi\n{resources}\n"
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
        "EROL · {name}\n{root}\n{resources}\n"
        "/help commands · /connect connections · /language auto|en|tr\n",
        "EROL · {name}\n{root}\n{resources}\n"
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
    "start": "Guided setup: connections, project, model and language",
    "menu": "Action menu: project, model, saved chats, files and reading layout",
    "help": "Show commands and examples",
    "project": "Show/select project: /project C:/Projects/my-app (quote spaces)",
    "my-projects": "List/select projects: /my-projects | /my-projects 1 | /my-projects add PATH",
    "chats": "Saved chats: /chats | /chats 1 | /chats show 1 | /chats page 2",
    "rename": "Name a chat: /rename TITLE | /chats rename 1 TITLE",
    "general": "Switch to projectless conversation: /general [MESSAGE]",
    "research": "Projectless source research: /research [QUESTION or URL]",
    "connect": "Add CLI/API: /connect codex | /connect openai work OPENAI_API_KEY",
    "providers": "Check connection login/capabilities; /providers disable ID",
    "models": (
        "Model profiles; /models compare TASK | /models refresh | /models add ID JSON_PROFILE"
    ),
    "model": "List/select: /model | /model 1 | /model NAME | /model auto",
    "effort": "Reasoning effort: /effort auto | /effort high (supported values: /models)",
    "files": "Show the latest task's output files with absolute paths",
    "settings": "Show/change settings: /settings api_budget_usd 5",
    "plan": "Plan without execution: /plan TASK",
    "skills": "Override routing: /skills use NAME… | /skills auto",
    "diff": "Change summary; select file/page with /diff 1 or /diff 1 2",
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
