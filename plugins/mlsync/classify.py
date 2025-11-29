from ranger.api.commands import Command
from pathlib import Path
import shutil
import json
import os

RULE_PATH = os.path.expanduser("~/.config/ranger/plugins/mlsync/rules.json")

def load_rules():
    """讀取 rules.json；若不存在則使用預設"""
    if os.path.exists(RULE_PATH):
        with open(RULE_PATH, "r") as f:
            return json.load(f)
    return {
        "images": [".png", ".jpg", ".jpeg"],
        "checkpoints": [".pt", ".pth"],
        "configs": [".yaml", ".yml", ".json"],
        "logs": [".log", ".txt"]
    }

class classify(Command):
    """
    :classify ext
    :classify version [prefix_len]

    示例：
    :classify ext
    :classify version 6
    """

    def execute(self):
        args = self.args

        if len(args) < 2:
            self.fm.notify("Usage: classify <ext|version>", bad=True)
            return

        mode = args[1]
        cwd = Path(self.fm.thisdir.path)

        if mode == "ext":
            self.classify_ext(cwd)

        elif mode == "version":
            prefix_len = int(args[2]) if len(args) > 2 else 6
            self.classify_version(cwd, prefix_len)

        else:
            self.fm.notify(f"Unknown mode: {mode}", bad=True)

    # -----------------------------
    # 分類邏輯（依副檔名）
    # -----------------------------
    def classify_ext(self, base_dir: Path):
        rules = load_rules()
        moved_count = 0

        for item in base_dir.iterdir():
            if item.is_dir():
                continue

            ext = item.suffix.lower()
            target_subdir = None

            for folder, exts in rules.items():
                if ext in exts:
                    target_subdir = folder
                    break

            if not target_subdir:
                target_subdir = "others"

            dest_dir = base_dir / target_subdir
            dest_dir.mkdir(exist_ok=True)

            shutil.move(str(item), dest_dir / item.name)
            moved_count += 1

        self.fm.notify(f"Classified by extension. Files moved: {moved_count}")

    # -----------------------------
    # 分類邏輯（依前綴版號）
    # -----------------------------
    def classify_version(self, base_dir: Path, prefix_len: int):
        version_root = base_dir / "versions"
        version_root.mkdir(exist_ok=True)

        moved_count = 0

        for item in base_dir.iterdir():
            if item.is_dir():
                continue

            name = item.name
            if len(name) < prefix_len:
                dest_dir = version_root / "others"
            else:
                prefix = name[:prefix_len]
                dest_dir = version_root / prefix

            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), dest_dir / item.name)
            moved_count += 1

        self.fm.notify(
            f"Classified by version prefix({prefix_len}). Files moved: {moved_count}"
        )
