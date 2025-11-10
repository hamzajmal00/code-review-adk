from datetime import datetime

def log(message: str):
    """Lightweight console logger."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
