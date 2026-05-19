def format_currency_python(amount: float) -> str:
    return f"Rp {int(amount):,}".replace(",", ".")
