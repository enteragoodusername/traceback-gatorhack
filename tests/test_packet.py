import hashlib
import json
import zipfile
import pytest
from scripts.verify_packet import verify


def packet(path, *, alter=False, omit=False, no_match=False):
    frame = b"actual-image-bytes"
    report = {
        "results": []
        if no_match
        else [{"evidence": [{"queryImage": "query.jpg", "sourceImage": "query.jpg"}]}],
        "evidenceAssets": []
        if (omit or no_match)
        else [{"file": "query.jpg", "sha256": hashlib.sha256(frame).hexdigest()}],
    }
    raw = json.dumps(report).encode()
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("report.json", raw)
        archive.writestr(
            "report.sha256", hashlib.sha256(raw).hexdigest() + "  report.json\n"
        )
        archive.writestr("frames/query.jpg", b"changed" if alter else frame)


def test_verifies_an_intact_packet(tmp_path):
    path = tmp_path / "evidence.zip"
    packet(path)
    assert verify(path) == 1


def test_detects_changed_image(tmp_path):
    path = tmp_path / "evidence.zip"
    packet(path, alter=True)
    with pytest.raises(ValueError, match="Checksum mismatch"):
        verify(path)


def test_rejects_missing_evidence_inventory(tmp_path):
    path = tmp_path / "evidence.zip"
    packet(path, omit=True)
    with pytest.raises(ValueError, match="inventory"):
        verify(path)


def test_no_match_report_can_have_no_images(tmp_path):
    path = tmp_path / "evidence.zip"
    packet(path, no_match=True)
    assert verify(path) == 0
