# -----------------------------------------------------------------------------
# Ranger Plugin: ssh_download (Final Fix for Tar Loop)
# -----------------------------------------------------------------------------

import os
import shlex
import tempfile
import shutil
import time
from datetime import datetime
from ranger.api.commands import Command
from ranger.core.loader import CommandLoader

class ssh_download(Command):
    """
    :ssh_download <destination> [flags]
    """

    def execute(self):
        # 1. 取得選取檔案
        selection = self.fm.thistab.get_selection()
        if not selection:
            self.fm.notify("Error: No files selected", bad=True)
            return

        # 2. 參數解析
        args = self.args[1:]
        dest = None
        port = "2222"
        mode = "none" 
        sep_char = "_"

        skip = False
        for i, arg in enumerate(args):
            if skip:
                skip = False
                continue
            if arg == '-e':
                mode = 'ext'
            elif arg == '-d':
                mode = 'date'
            elif arg == '-s':
                mode = 'sep'
                if i + 1 < len(args):
                    sep_char = args[i+1]
                    skip = True
            elif arg == '-P':
                if i + 1 < len(args):
                    port = args[i+1]
                    skip = True
            elif not dest:
                dest = arg

        if not dest:
            self.fm.notify("請指定目標...", bad=True)
            self.fm.ui.console.open(f"{self.get_name()} user@localhost:~/Desktop -e")
            return

        # 3. 建立暫存資料夾 (存放 symlink 結構)
        temp_root = tempfile.mkdtemp()
        
        try:
            self.fm.notify(f"正在分類 ({mode}) 並打包...")

            # --- 分類邏輯 ---
            for f in selection:
                sub_folder = "Misc"
                if mode == 'none':
                    sub_folder = "."
                elif mode == 'ext':
                    sub_folder = f.extension.lower() if f.extension else "no_ext"
                elif mode == 'date':
                    mtime = f.stat.st_mtime
                    sub_folder = datetime.fromtimestamp(mtime).strftime('%Y-%m')
                elif mode == 'sep':
                    if sep_char in f.basename:
                        sub_folder = f.basename.split(sep_char)[0]
                    else:
                        sub_folder = "Other"

                target_dir = os.path.join(temp_root, sub_folder)
                os.makedirs(target_dir, exist_ok=True)

                target_link = os.path.join(target_dir, f.basename)
                if not os.path.exists(target_link):
                    os.symlink(f.path, target_link)

            # --- 4. 組合指令 (關鍵修正) ---
            
            # 修正點：壓縮檔不要放在 temp_root 裡面，改放在 /tmp (temp_root 的外面)
            # 這樣 tar 打包 temp_root 時就不會打包到自己，也不會造成目錄變動錯誤
            timestamp = int(time.time())
            archive_name = f"download_{timestamp}.tar.gz"
            archive_path = os.path.join("/tmp", archive_name)
            
            # 指令邏輯：
            # 1. cd 進暫存目錄
            # 2. tar 打包內容到【外部】的 archive_path
            # 3. scp 傳輸那個外部檔案
            # 4. 刪除外部檔案 & 刪除暫存目錄
            
            cmd = (
                f"cd {shlex.quote(temp_root)} && "
                f"tar -czhf {shlex.quote(archive_path)} . && "
                f"scp -P {port} -o StrictHostKeyChecking=no -o ConnectTimeout=10 {shlex.quote(archive_path)} {dest} && "
                f"rm {shlex.quote(archive_path)} && "
                f"rm -rf {shlex.quote(temp_root)}"
            )

            # --- 5. 執行 ---
            # 如果你還沒搞定 SSH Key 免密碼，請繼續用 flags='w'
            # 如果搞定了，可以改回 CommandLoader
            self.fm.execute_command(cmd, flags='w')

        except Exception as e:
            self.fm.notify(f"Error: {e}", bad=True)
            if os.path.exists(temp_root):
                shutil.rmtree(temp_root)
