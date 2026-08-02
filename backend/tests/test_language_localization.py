from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

USER_FACING_FILES = [
    "frontend/src/pages/UserManagementPage.tsx",
    "frontend/src/pages/TargetsPage.tsx",
    "frontend/src/components/dashboard/TargetsTable.tsx",
    "frontend/src/services/authService.ts",
    "frontend/src/services/dashboardService.ts",
    "mini-app/index.html",
    "mini-app/js/app.js",
    "backend/bot_service.py",
    "backend/routers/auth.py",
    "backend/routers/targets.py",
    "backend/routers/officer.py",
    "backend/agent_tools.py",
]

DISALLOWED_ENGLISH_PHRASES = [
    "Access Verification",
    "Active Cases",
    "Amount Due",
    "Assignment Queue",
    "Available commands",
    "Cancel",
    "Classification",
    "Collection statistics",
    "Confirm Password",
    "Customer Name",
    "Daily Summary",
    "Enter officer name",
    "Enter Telegram ID",
    "Evidentiary Documentation",
    "Failed to",
    "Field Observation",
    "Field Officers",
    "Finalize Submission",
    "Full Name",
    "Initializing System",
    "Invalid username or password",
    "Issue Report",
    "Loading Personnel Records",
    "Network Status",
    "No matching records",
    "No registered personnel",
    "Officer Narrative",
    "Open Web Dashboard",
    "Password changed successfully",
    "Personnel Directory",
    "Recent Field Reports",
    "Register Officer",
    "Registered Personnel",
    "Report Submission",
    "Required for Mini App access and notifications",
    "Save",
    "Search name or ID",
    "Subject Data",
    "Target assigned",
    "Verify Identity",
    "Welcome",
]


# Prefixes/markers that identify a line as developer-only (not shown to users),
# so an English phrase there is not a localization defect.
_COMMENT_PREFIXES = ("//", "#", "<!--", "-->", "*", "/*")


def _is_non_user_facing(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.startswith(_COMMENT_PREFIXES):
        return True
    # console.log/error/warn, print(), and logger.* are diagnostics, never user copy
    if "console." in s or s.startswith("print(") or "logger." in s:
        return True
    return False


def test_user_facing_copy_is_indonesian():
    offenders = []

    for relative_path in USER_FACING_FILES:
        for lineno, line in enumerate(
            (ROOT / relative_path).read_text(encoding="utf-8").splitlines(), 1
        ):
            if _is_non_user_facing(line):
                continue
            for phrase in DISALLOWED_ENGLISH_PHRASES:
                if phrase in line:
                    offenders.append(f"{relative_path}:{lineno}: {phrase}")

    assert offenders == [], f"English user-facing copy found: {offenders}"


# --- Opsi bahasa (portal manajer) --------------------------------------------
# Bahasa Inggris boleh ada, tapi HANYA di dalam kamus terjemahan, dan Indonesia
# harus tetap jadi default. Tiga tes di bawah menjaga kedua syarat itu.

_I18N = ROOT / "frontend/src/lib/i18n.ts"
_LANG_CTX = ROOT / "frontend/src/contexts/LanguageContext.tsx"


def test_indonesian_stays_the_default_language():
    """Kalau default bergeser ke Inggris, seluruh portal berubah bahasa diam-diam."""
    ctx = _LANG_CTX.read_text(encoding="utf-8")
    assert 'useState<Lang>' in ctx
    assert '"en" ? "en" : "id"' in ctx, "default bahasa harus jatuh ke 'id'"

    i18n = _I18N.read_text(encoding="utf-8")
    assert 'if (lang === "id") return text;' in i18n, (
        "mode Indonesia harus mengembalikan teks apa adanya, tanpa lewat kamus"
    )


def test_missing_translation_falls_back_to_indonesian():
    """String yang belum diterjemahkan harus jatuh ke Indonesia, bukan kunci mentah."""
    i18n = _I18N.read_text(encoding="utf-8")
    assert "EN[text] ?? text" in i18n, (
        "translate() harus punya fallback ke teks aslinya"
    )


def test_translation_keys_still_exist_in_the_ui():
    """Kunci kamus yang sudah tidak dipakai di UI = kamus mulai basi.

    Dicek longgar: cukup ada satu file frontend yang masih memuat teksnya.
    """
    import re

    entries = re.findall(r'^\s+"((?:[^"\\]|\\.)+)":', _I18N.read_text(encoding="utf-8"), re.M)
    assert entries, "kamus EN kosong"

    haystack = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (ROOT / "frontend/src").rglob("*.tsx")
    )

    stale = [e for e in entries if e.replace('\\"', '"') not in haystack]
    assert stale == [], f"kunci kamus tidak lagi dipakai di UI: {stale[:10]}"
