import cv2
import os
import json
import subprocess
import sys
import zlib
import pysubs2
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

OUT_DIR = "frames"
COLS, ROWS = 120, 40
MAGIC = b"ZLIBFRAME"

SUBS = None
FPS = None


def download(url):
    print("Downloading video...")
    subprocess.run([
        "yt-dlp",
        "--no-playlist",
        "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "--merge-output-format", "mp4",
        "-o", "video.mp4",
        url,
    ], check=True)

    print("Downloading subtitles...")
    subprocess.run([
        "yt-dlp",
        "--no-playlist",
        "--write-auto-sub", "--sub-lang", "en",
        "--convert-subs", "srt",
        "--skip-download",
        "-o", "video",
        url,
    ])

    if os.path.exists("video.en.srt"):
        os.rename("video.en.srt", "video.srt")


def init_worker(subs, fps):
    global SUBS, FPS
    SUBS = subs
    FPS = fps


def process_frame(index):
    cap = cv2.VideoCapture("video.mp4")
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return

    time_ms = (index / FPS) * 1000
    small = cv2.resize(frame, (COLS, ROWS * 2))

    lines = []
    for y in range(0, ROWS * 2, 2):
        line = ""
        for x in range(COLS):
            tr, tg, tb = small[y, x][::-1]
            br, bg, bb = small[y + 1, x][::-1]
            line += (
                f"\033[38;2;{tr};{tg};{tb};"
                f"48;2;{br};{bg};{bb}m▀"
            )
        lines.append(line)

    ascii_frame = "\033[0m\n".join(lines) + "\033[0m"

    sub_text = ""
    for start, end, text in SUBS:
        if start <= time_ms <= end:
            sub_text = text
            break

    if sub_text:
        sub_lines = sub_text.split("\n")
        sub_block = "\n".join(
            f"\033[1;37m{s.center(COLS)}\033[0m" for s in sub_lines
        )
        ascii_frame += "\n" + sub_block
    else:
        ascii_frame += "\n" + " " * COLS

    payload = MAGIC + zlib.compress(f"\033[H\033[2J{ascii_frame}\n".encode(), 6)

    with open(os.path.join(OUT_DIR, f"{index:06d}.bin"), "wb") as f:
        f.write(payload)


def generate(url):
    download(url)

    os.makedirs(OUT_DIR, exist_ok=True)
    cap = cv2.VideoCapture("video.mp4")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    subs = []
    if os.path.exists("video.srt"):
        subs = [
            (e.start, e.end, e.plaintext)
            for e in pysubs2.load("video.srt")
        ]
    else:
        print("No subtitles found, continuing without.")

    workers = min(cpu_count(), 2)
    with Pool(workers, initializer=init_worker, initargs=(subs, fps)) as pool:
        list(tqdm(
            pool.imap(process_frame, range(total)),
            total=total,
            desc="Generating",
        ))

    with open(os.path.join(OUT_DIR, "meta.json"), "w") as f:
        json.dump({"fps": fps, "total": total}, f)

    print(f"Done: {total} frames at {fps} fps")
    print("Run: python serve.py")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <youtube-url>")
        sys.exit(1)
    generate(sys.argv[1])