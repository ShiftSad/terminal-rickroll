import os
import zlib
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

FRAMES_DIR = "frames"
MAGIC = b"ZLIBFRAME"


def compress_file(name):
    path = os.path.join(FRAMES_DIR, name)
    with open(path, "rb") as f:
        data = f.read()

    if data[:len(MAGIC)] == MAGIC:
        return "skipped"

    compressed = MAGIC + zlib.compress(data, 6)
    with open(path, "wb") as f:
        f.write(compressed)
    return "compressed"


if __name__ == "__main__":
    bins = sorted(
        f for f in os.listdir(FRAMES_DIR)
        if f.endswith(".bin")
    )

    compressed = skipped = 0
    with Pool(cpu_count()) as pool:
        for result in tqdm(
            pool.imap(compress_file, bins, chunksize=32),
            total=len(bins),
            desc="Compressing",
        ):
            if result == "skipped":
                skipped += 1
            else:
                compressed += 1

    print(f"Done. {compressed} compressed, {skipped} already compressed.")
