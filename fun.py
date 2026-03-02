from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json
import time
import zlib

FRAMES_DIR = "frames"
MAGIC = b"ZLIBFRAME"

with open(os.path.join(FRAMES_DIR, "meta.json")) as f:
    meta = json.load(f)

FPS = meta["fps"]
TOTAL = meta["total"]

print(f"Loading {TOTAL} frames...")
FRAMES = []
for i in range(TOTAL):
    with open(os.path.join(FRAMES_DIR, f"{i:06d}.bin"), "rb") as f:
        FRAMES.append(zlib.decompress(f.read()[len(MAGIC):]))
print(f"Loaded. Serving at {FPS} fps")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

        try:
            while True:
                for frame in FRAMES:
                    self.wfile.write(frame)
                    self.wfile.flush()
                    time.sleep(1 / FPS)
        except BrokenPipeError:
            pass


HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()