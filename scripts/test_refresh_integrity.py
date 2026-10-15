"""Run the real refresh shell and compute gate with a corrupted simulated source."""
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_corrupted_otemachi_stops_refresh_before_export_and_commit(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(ROOT / "scripts/refresh-ratings.sh", scripts / "refresh-ratings.sh")
    # Read-only preflights are tested separately; this harness has no credentials
    # or live stores. Run the production compute main against simulated inputs.
    for name in ("check-rating-schema.py", "check-rating-sources.py"):
        (scripts / name).write_text("pass\n")
    (scripts / "export-ratings.py").write_text("raise AssertionError('export must not run')\n")
    driver = f'''
import importlib.util, sys, types
from datetime import date
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'scripts')!r})
stations = [{{"slug":s,"lat":35.68,"lng":139.76,"prefecture":"Tokyo","line_count":2}}
            for s in ("otemachi", "plain")]
class DB:
    def __init__(self, table):
        assert table != "computed_ratings", "Must fail before computed store access"
    def get_all_records(self):
        return [{{"slug":s["slug"], "scraped_at":date.today().isoformat(), "food_count":10,
                 "total_count":10,"izakaya_count":2,"bar_count":2,"cafe_count":2,"midnight_count":2}}
                for s in stations]
utils = types.ModuleType("utils")
utils.NocoDB = DB
utils.load_stations = lambda: stations
sys.modules["utils"] = utils
spec = importlib.util.spec_from_file_location("compute", {str(ROOT / 'scripts/compute-ratings.py')!r})
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)
cr.load_station_safety = lambda: ({{s:{{"rate":rate,"confidence":"strong","source":"fixture"}}
                                       for s,rate in (("otemachi",1000),("plain",1))}}, "2024")
cr.load_passengers = lambda: ({{}}, "2024")
cr.load_rent_data = lambda: {{}}
cr.main()
'''
    (scripts / "compute-ratings.py").write_text(driver)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    python = binaries / "python3"
    python.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} \"$@\"\n")
    python.chmod(0o755)
    git = binaries / "git"
    git.write_text('''#!/bin/sh
case "$1" in
  rev-parse) echo fixture-branch ;;
  rev-list) echo 0 ;;
  commit) touch COMMIT_WAS_REACHED; exit 99 ;;
esac
''')
    git.chmod(0o755)
    env = {**os.environ, "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
           "NOCODB_API_TOKEN": "offline-synthetic-only"}
    result = subprocess.run(["bash", str(scripts / "refresh-ratings.sh"), "--auto", "--no-build",
                             "--max-source-age-days=90"], cwd=tmp_path, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "spot-check divergence" in result.stderr
    assert "otemachi" in result.stdout and "computed=1 expected~9" in result.stdout
    assert "Running export" not in result.stdout
    assert not (tmp_path / "COMMIT_WAS_REACHED").exists()
