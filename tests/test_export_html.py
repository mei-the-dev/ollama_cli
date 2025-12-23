import json
from pathlib import Path

from scripts.export_report_html import export_html


def test_export_html(tmp_path):
    rpt = {"generated_at":"t","cards":[{"test":"t1","prompt":"p","answer":"a","parsed_tool":None}]}
    r = tmp_path / "report.json"
    r.write_text(json.dumps(rpt))
    out = tmp_path / "report.html"
    export_html(str(r), str(out))
    assert out.exists()
    s = out.read_text()
    assert "Test Report" in s and "t1" in s and "p" in s
