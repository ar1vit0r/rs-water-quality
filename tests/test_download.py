import urllib.error
from pathlib import Path

import pytest

from rs_water_quality.datasets import DATASETS
from rs_water_quality.download import download


def test_download_failure_names_url_and_points_to_readme(tmp_path: Path, monkeypatch):
    def refuse(url, timeout):
        raise urllib.error.HTTPError(url, 400, "Bad Request", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", refuse)
    ds = DATASETS[0]

    with pytest.raises(RuntimeError, match="README") as info:
        download(ds, tmp_path, retries=2)

    assert ds.url in str(info.value)
    assert not (tmp_path / f"{ds.indicator}.csv").exists()
