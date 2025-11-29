from ranger.api.commands import Command
from pathlib import Path
import shutil
import subprocess
import os

class download(Command):
    """
    :download [ext|version]

    功能：
    1. (可選) 自動分類
    2. 自動打包 tar.gz
    3. 自動 SCP 傳本地端

    使用者需先 export：
    export DL_HOST=192.168.0.5
    export DL_USER=alexei
    export DL_TARGET=/Users/alexei/Downloads/exp1
    """

    def execute(self):
        args = self.args
        cwd = Path(self.fm.thisdir.path).resolve()

        # 讀環境變數
        host = os.getenv("DL_HOST")
        user = os.getenv("DL_USER")
        target = os.getenv("DL_TARGET")

        if not (host and user and target):
            self.fm.notify("Please set DL_HOST / DL_USER / DL_TARGET", bad=True)
            return

        # Optional: 分類
        if len(args) > 1:
            mode = args[1]
            self.fm.execute_console(f"classify {mode}")

        # --------------------
        # 打包
        # --------------------
        archive_name = f"{cwd.name}.tar.gz"
        archive_path = shutil.make_archive(
            base_name=cwd.name,
            format="gztar",
            root_dir=cwd
        )

        self.fm.notify(f"Archive created: {archive_path}")

        # --------------------
        # SCP
        # --------------------
        remote = f"{user}@{host}:{target}"

        try:
            subprocess.run(["scp", archive_path, remote], check=True)
            self.fm.notify(f"Downloaded to local: {remote}", good=True)

        except Exception as e:
            self.fm.notify(f"SCP failed: {str(e)}", bad=True)
