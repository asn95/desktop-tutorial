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


def test_user_facing_copy_is_indonesian():
    offenders = []

    for relative_path in USER_FACING_FILES:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for phrase in DISALLOWED_ENGLISH_PHRASES:
            if phrase in text:
                offenders.append(f"{relative_path}: {phrase}")

    assert offenders == []
