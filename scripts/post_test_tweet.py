#!/usr/bin/env python3
"""Post one text-only tweet via the X API v2 with OAuth 1.0a.

Pure standard library, no dependencies. Reads the four OAuth 1.0a values
from the environment (GitHub Actions secrets in the workflow). Never prints
a secret, the Authorization header, or any credential value.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://api.x.com/2/tweets"


def pct(value):
    return urllib.parse.quote(str(value), safe="")


def build_auth_header(consumer_key, consumer_secret, token, token_secret):
    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    params = "&".join(pct(k) + "=" + pct(v) for k, v in sorted(oauth.items()))
    base = "POST&" + pct(API_URL) + "&" + pct(params)
    key = pct(consumer_secret) + "&" + pct(token_secret)
    digest = hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()
    oauth["oauth_signature"] = base64.b64encode(digest).decode()
    header = "OAuth " + ", ".join(
        pct(k) + '="' + pct(v) + '"' for k, v in sorted(oauth.items())
    )
    return header


def main():
    names = ["X_API_KEY", "X_API_KEY_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        print("missing required secret env vars: " + ", ".join(missing), file=sys.stderr)
        return 2
    text = os.environ.get("TWEET_TEXT", "").strip()
    if not text:
        print("TWEET_TEXT is empty", file=sys.stderr)
        return 2
    if len(text) > 280:
        print("TWEET_TEXT is %d chars, over the 280 limit" % len(text), file=sys.stderr)
        return 2
    header = build_auth_header(
        os.environ["X_API_KEY"],
        os.environ["X_API_KEY_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    body = json.dumps({"text": text}).encode()
    request = urllib.request.Request(API_URL, data=body, method="POST")
    request.add_header("Authorization", header)
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        print("X API error: HTTP %d" % exc.code, file=sys.stderr)
        print(exc.read().decode()[:2000], file=sys.stderr)
        return 1
    data = payload.get("data", {})
    tweet_id = data.get("id")
    if not tweet_id:
        print("unexpected response: " + json.dumps(payload)[:1000], file=sys.stderr)
        return 1
    print("posted tweet id: " + tweet_id)
    print("tweet url: https://x.com/velix_xyz/status/" + tweet_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
