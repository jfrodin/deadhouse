"""Windows entry point (also used by PyInstaller). Writes a crash log next to the executable."""
import os
import sys
import traceback


def main():
    try:
        from deadhouse.game import run
        return run()
    except SystemExit:
        raise
    except Exception:
        base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
        path = os.path.join(base, "deadhouse_crash.log")
        with open(path, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Deadhouse crashed. Details were written to:\n{path}", "Deadhouse", 0x10)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
