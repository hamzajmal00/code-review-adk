import os
import shutil
import stat
from utils.logger import log

def remove_readonly(func, path, _):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        log(f"⚠️ Could not remove {path}: {e}")

def safe_rmtree(path):
    try:
        shutil.rmtree(path, onerror=remove_readonly)
        log(f"🧹 Cleaned {path}")
    except Exception as e:
        log(f"⚠️ Cleanup failed for {path}: {e}")
