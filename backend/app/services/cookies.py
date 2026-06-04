from pathlib import Path
import os
import base64
from ..core.data_extraction import _resolve_cookie_path
import logging

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
logger = logging.getLogger(__name__)

def initialize_cookies():
    yt_b64 = os.getenv("YT_COOKIES_BASE64")
    insta_b64 = os.getenv("INSTA_COOKIES_BASE64")

    if yt_b64 and yt_b64.strip():
        try:
            yt_path = _resolve_cookie_path("youtube.com")
            # Ensure parent directories exist
            Path(yt_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(yt_path, "wb") as f:
                f.write(base64.b64decode(yt_b64.strip()))
            
            os.chmod(yt_path, 0o600)
            logger.info(f"Successfully initialized YouTube cookies at {yt_path}")
        except Exception as e:
            logger.error(f"Failed to write YouTube cookies: {str(e)}")

    if insta_b64 and insta_b64.strip():
        try:
            insta_path = _resolve_cookie_path("instagram.com")
            Path(insta_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(insta_path, "wb") as f:
                f.write(base64.b64decode(insta_b64.strip()))
            
            os.chmod(insta_path, 0o600)
            logger.info(f"Successfully initialized Instagram cookies at {insta_path}")
        except Exception as e:
            logger.error(f"Failed to write Instagram cookies: {str(e)}")