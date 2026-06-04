from pathlib import Path
import os
import base64
from ..core.data_extraction import _resolve_cookie_path

## Windows
# def initialize_cookies():
#     backend_root = Path(__file__).resolve().parents[2]
#     yt_b64 = os.getenv("YT_COOKIES_BASE64")
#     insta_b64 = os.getenv("INSTA_COOKIES_BASE64")

#     if yt_b64:
#         yt_path = backend_root / "youtube_cookies.txt"
#         with open(yt_path, "wb") as f:
#             f.write(base64.b64decode(yt_b64))
#         # try:
#         #     os.chmod(yt_path, 0o600)
#         # except Exception:
#         #     pass
            
#     if insta_b64:
#         insta_path = backend_root / "instagram_cookies.txt"
#         with open(insta_path, "wb") as f:
#             f.write(base64.b64decode(insta_b64))
#         # try:
#         #     os.chmod(insta_path, 0o600)
#         # except Exception:
#         #     pass

## development
def initialize_cookies():
    yt_b64 = os.getenv("YT_COOKIES_BASE64")
    insta_b64 = os.getenv("INSTA_COOKIES_BASE64")

    if yt_b64:
        yt_path = _resolve_cookie_path("youtube.com")
        
        with open(yt_path, "wb") as f:
            f.write(base64.b64decode(yt_b64))
        try:
            os.chmod(yt_path, 0o600)
        except Exception:
            pass
            
    if insta_b64:
        insta_path = _resolve_cookie_path("instagram.com")
        
        with open(insta_path, "wb") as f:
            f.write(base64.b64decode(insta_b64))
        try:
            os.chmod(insta_path, 0o600)
        except Exception:
            pass