import json

import numpy as np

from vibewatch.cli import main

READINGS = """asset_id,timestamp,velocity_rms_mm_s
pump-1,2026-09-01T08:00:00,1.0
pump-1,2026-09-02T08:00:00,1.0
pump-1,2026-09-03T08:00:00,1.0
gearbox-4,2026-09-01T08:00:00,3.0
gearbox-4,2026-09-02T08:00:00,3.6
gearbox-4,2026-09-03T08:00:00,4.7
"""


def test_report_lists_worst_asset_first_and_exits_nonzero_on_alarm(tmp_path, capsys):
    path = tmp_path / "readings.csv"
    path.write_text(READINGS)
    code = main(["report", str(path)])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 1
    assert lines[0].startswith("alarm") and "gearbox-4" in lines[0]
    assert lines[1].startswith("ok") and "pump-1" in lines[1]


def test_report_json(tmp_path, capsys):
    path = tmp_path / "readings.csv"
    path.write_text(READINGS)
    main(["report", str(path), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert [d["asset_id"] for d in data] == ["gearbox-4", "pump-1"]
    assert data[0]["zone"] == "D"


def test_bad_row_names_the_line(tmp_path):
    path = tmp_path / "readings.csv"
    path.write_text("asset_id,timestamp,velocity_rms_mm_s\npump-1,not-a-date,1.0\n")
    try:
        main(["report", str(path)])
    except SystemExit as exc:
        assert ":2:" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_waveform_command(tmp_path, capsys):
    fs = 2048
    t = np.arange(fs) / fs
    path = tmp_path / "capture.csv"
    path.write_text("accel_m_s2\n" + "\n".join(f"{v:.6f}" for v in 10 * np.sin(2 * np.pi * 50 * t)))
    assert main(["waveform", str(path), "--fs", str(fs)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert abs(out["velocity_rms_mm_s"] - 22.508) < 0.05
    assert out["zone"] == "D"
    assert out["peak_frequency_hz"] == 50.0
