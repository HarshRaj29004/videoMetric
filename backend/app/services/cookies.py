import os
import base64

def initialize_cookies():
    yt_b64 = os.getenv("YT_COOKIES_BASE64")
    insta_b64 = os.getenv("INSTA_COOKIES_BASE64")

    if yt_b64:
        with open("/tmp/youtube_cookies.txt", "wb") as f:
            f.write(base64.b64decode(yt_b64))
        os.chmod("/tmp/youtube_cookies.txt", 0o600)
            
    if insta_b64:
        with open("instagram_cookies.txt", "wb") as f:
            f.write(base64.b64decode(insta_b64))
        os.chmod("/tmp/instagram_cookies.txt",0o600)