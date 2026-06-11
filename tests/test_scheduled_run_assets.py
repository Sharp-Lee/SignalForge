import os
import plistlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_scheduled_wrapper_is_executable_and_redacts_logs():
    script_path = ROOT / "scripts" / "run_scheduled.sh"
    script = script_path.read_text()

    assert os.access(script_path, os.X_OK)
    assert "scripts/run_live.py" in script
    assert "NEWS_RUN_MODE" in script
    assert "--capture --store" in script
    assert "--analyze" in script
    assert "--pipeline" in script
    assert "--show-store" in script
    assert ".local/runtime.env" in script
    assert ".config/news-llm/keys.env" in script
    assert ".local/news-data/live-store.db" in script
    assert "NEWS_RSS_SOURCES_FILE" in script
    assert "NEWS_ANALYZE_TOP_K" in script
    assert "keys.env" in script
    assert "sed -E" in script
    assert "***REDACTED***" in script
    assert not re.search(r"sk-[A-Za-z0-9_-]{10,}", script)


def test_capture_launchd_plist_calls_wrapper_four_times_without_run_at_load():
    plist_path = ROOT / "launchd" / "com.wukong.news-capture.plist"
    with plist_path.open("rb") as f:
        plist = plistlib.load(f)

    assert plist["Label"] == "com.wukong.news-capture"
    assert plist["ProgramArguments"] == [
        "/bin/bash",
        str(ROOT / "scripts" / "run_scheduled.sh"),
    ]
    assert plist["EnvironmentVariables"] == {"NEWS_RUN_MODE": "capture"}
    assert plist["StartCalendarInterval"] == [
        {"Hour": 8, "Minute": 30},
        {"Hour": 12, "Minute": 30},
        {"Hour": 16, "Minute": 30},
        {"Hour": 21, "Minute": 30},
    ]
    assert plist["RunAtLoad"] is False
    assert plist["StandardOutPath"] == "/dev/null"
    assert plist["StandardErrorPath"] == "/dev/null"

    serialized = plist_path.read_text()
    assert not re.search(r"sk-[A-Za-z0-9_-]{10,}", serialized)


def test_analyze_launchd_plist_calls_wrapper_daily_without_run_at_load():
    plist_path = ROOT / "launchd" / "com.wukong.news-analyze.plist"
    with plist_path.open("rb") as f:
        plist = plistlib.load(f)

    assert plist["Label"] == "com.wukong.news-analyze"
    assert plist["ProgramArguments"] == [
        "/bin/bash",
        str(ROOT / "scripts" / "run_scheduled.sh"),
    ]
    assert plist["EnvironmentVariables"] == {"NEWS_RUN_MODE": "analyze"}
    assert plist["StartCalendarInterval"] == {"Hour": 18, "Minute": 0}
    assert plist["RunAtLoad"] is False
    assert plist["StandardOutPath"] == "/dev/null"
    assert plist["StandardErrorPath"] == "/dev/null"

    serialized = plist_path.read_text()
    assert not re.search(r"sk-[A-Za-z0-9_-]{10,}", serialized)
