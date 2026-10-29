import hashlib
import urllib.request
from pathlib import Path

from rs_water_quality.datasets import Dataset


def download(
    dataset: Dataset, dest_dir: Path, retries: int = 2, timeout: int = 120
) -> tuple[Path, str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{dataset.indicator}.csv"

    data = b""
    for attempt in range(1, retries + 1):
        try:
            resp = urllib.request.urlopen(dataset.url, timeout=timeout)
            data = resp.read()
            break
        except Exception as exc:
            if attempt == retries:
                raise RuntimeError(
                    f"cannot download {dataset.url}: {exc}. "
                    "The ANA source may have been retired, see README (Data sources)."
                ) from exc

    dest.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    return dest, sha
