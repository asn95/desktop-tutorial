def format_currency_python(amount: float) -> str:
    return f"Rp {int(amount):,}".replace(",", ".")


def normalize_phone(raw) -> str | None:
    """Seragamkan nomor Indonesia menjadi '62…' tanpa tanda plus.

    Telegram mengirim '628123456789' lewat kartu kontak, sedangkan manajer mengetik
    '0812-3456-789', '+62 812 3456 789', atau '812…'. Tanpa penyeragaman ini
    pencocokan saat petugas menautkan Telegram-nya sendiri tidak akan pernah kena,
    dan pemeriksaan keunikan di API bisa dilewati hanya dengan mengubah tanda hubung.
    """
    if not raw:
        return None
    digits = "".join(c for c in str(raw) if c.isdigit())
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]         # awalan panggilan internasional: 0062… → 62…
    if digits.startswith("0"):
        digits = "62" + digits[1:]  # 0812… → 62812…
    elif not digits.startswith("62"):
        digits = "62" + digits      # 812… → 62812…
    return digits
