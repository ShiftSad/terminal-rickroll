from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json
import time
import zlib
import gzip

FRAMES_DIR = "frames"
MAGIC = b"ZLIBFRAME"

with open(os.path.join(FRAMES_DIR, "meta.json")) as f:
    meta = json.load(f)

FPS = meta["fps"]
TOTAL = meta["total"]

print(f"Loading {TOTAL} frames...")
FRAMES = []
FRAMES_GZIP = []
for i in range(TOTAL):
    with open(os.path.join(FRAMES_DIR, f"{i:06d}.bin"), "rb") as f:
        raw = zlib.decompress(f.read()[len(MAGIC):])
        FRAMES.append(raw)
        FRAMES_GZIP.append(gzip.compress(raw))
print(f"Loaded. Serving at {FPS} fps")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        accept_encoding = self.headers.get("Accept-Encoding", "")
        use_gzip = any(
            part.split(";")[0].strip() == "gzip"
            for part in accept_encoding.split(",")
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()

        frames = FRAMES_GZIP if use_gzip else FRAMES
        try:
            while True:
                for frame in frames:
                    self.wfile.write(frame)
                    self.wfile.flush()
                    time.sleep(1 / FPS)
        except BrokenPipeError:
            pass


HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()