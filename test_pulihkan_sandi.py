"""Uji pembacaan kata sandi di pulihkan_sandi.py.

Dijalankan di bawah pseudo-terminal, karena yang diuji justru perilaku terminal:
kata sandi harus terbaca utuh, TIDAK boleh tergema ke layar, dan echo harus
dinyalakan kembali setelah selesai. Versi awal skrip ini gagal pada ketiganya
dengan cara yang berbeda-beda, jadi ketiganya diperiksa.

    python3 test_pulihkan_sandi.py     (atau lewat pytest)
"""
import os
import pty
import sys

SKRIP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pulihkan_sandi.py")
RAHASIA = "Rahasia#Panjang2026"


def _anak():
    import importlib.util as u
    spec = u.spec_from_file_location("pulihkan_sandi", SKRIP)
    mod = u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import termios

    hasil = mod.sandi("Kata sandi: ")
    echo = bool(termios.tcgetattr(sys.stdin.fileno())[3] & termios.ECHO)
    print(f"TERBACA={hasil!r} ECHO={echo}")
    sys.stdout.flush()
    os._exit(0)


def _jalankan():
    pid, fd = pty.fork()
    if pid == 0:
        _anak()

    # Tunggu prompt muncul dulu, meniru manusia. Mengetik lebih awal akan
    # tergema oleh line discipline sebelum skrip sempat mematikan echo.
    awal = b""
    while b"Kata sandi: " not in awal:
        awal += os.read(fd, 1024)
    os.write(fd, RAHASIA.encode() + b"\n")

    sisa = b""
    try:
        while True:
            d = os.read(fd, 1024)
            if not d:
                break
            sisa += d
    except OSError:      # pty ditutup saat anak keluar — wajar di macOS
        pass
    os.waitpid(pid, 0)
    return sisa.decode(errors="replace")


def test_sandi_tidak_tergema_dan_echo_dipulihkan():
    out = _jalankan()
    assert f"TERBACA={RAHASIA!r}" in out, f"kata sandi tidak terbaca utuh: {out!r}"
    assert "ECHO=True" in out, "echo tidak dinyalakan lagi — terminal ditinggalkan bisu"
    sebelum_lapor = out.split("TERBACA=")[0]
    assert RAHASIA not in sebelum_lapor, f"kata sandi TERGEMA ke layar: {sebelum_lapor!r}"


if __name__ == "__main__":
    test_sandi_tidak_tergema_dan_echo_dipulihkan()
    print("LULUS: terbaca utuh, tidak tergema, echo dipulihkan")
