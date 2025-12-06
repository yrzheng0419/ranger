# -----------------------------------------------------------------------------
# Ranger Plugin: ML Priority, Date Manager & SSH Smart Download
# Description: 
#   1. ssh_download: Recursive download with auto-sorting (Ext/Date/Prefix)
#   2. priority: Dynamic priority sorting (best model, error logs...)
#   3. sort_date: Sort files by date prefix (Newest first)
#   4. mark_date: Select files by date prefix
# -----------------------------------------------------------------------------

import os
import shlex
import tempfile
import shutil
import time
from datetime import datetime
from ranger.api.commands import Command
from ranger.container.directory import Directory

# =============================================================================
# Feature 1: SSH Smart Download (Recursive Fix + Tar Fix)
# =============================================================================

class ssh_download(Command):
    """
    :ssh_download <destination> [flags]

    Download files/folders via SSH with auto-sorting.
    
    Flags:
    -e          : Sort by Extension (jpg/, log/)
    -d          : Sort by Date (YYYY-MM/)
    -s <char>   : Sort by Separator Prefix (ProjectA_ -> ProjectA/)
    -P <port>   : SSH Port (default: 22)
    """

    def execute(self):
        # 1. Get selection
        selection = self.fm.thistab.get_selection()
        if not selection:
            self.fm.notify("Error: No files selected", bad=True)
            return

        # 2. Parse arguments
        args = self.args[1:]
        dest = None
        port = "2222"
        mode = "none" # none, ext, date, sep
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
            self.fm.notify("Please specify destination (e.g., user@host:~/Desktop)", bad=True)
            return

        # 3. Create temp directory for sorting structure
        temp_root = tempfile.mkdtemp()
        
        try:
            self.fm.notify(f"Processing download ({mode})...")

            # --- Helper: Link single file to temp structure ---
            def process_file(file_path, file_basename):
                sub_folder = "Misc"
                
                # Sorting Logic
                if mode == 'none':
                    sub_folder = "."
                elif mode == 'ext':
                    # Extract extension manually since we might get paths from os.walk
                    _, ext = os.path.splitext(file_basename)
                    sub_folder = ext.lstrip('.').lower() if ext else "no_ext"
                elif mode == 'date':
                    try:
                        mtime = os.stat(file_path).st_mtime
                        sub_folder = datetime.fromtimestamp(mtime).strftime('%Y-%m')
                    except:
                        sub_folder = "unknown_date"
                elif mode == 'sep':
                    if sep_char in file_basename:
                        sub_folder = file_basename.split(sep_char)[0]
                    else:
                        sub_folder = "Other"

                # Create target dir in temp_root
                target_dir = os.path.join(temp_root, sub_folder)
                os.makedirs(target_dir, exist_ok=True)

                # Create symlink
                target_link = os.path.join(target_dir, file_basename)
                if not os.path.exists(target_link):
                    os.symlink(file_path, target_link)

            # --- Main Loop: Recursive Handling ---
            for f in selection:
                if f.is_directory:
                    # Recursively walk through directory
                    for root, dirs, files in os.walk(f.path):
                        for filename in files:
                            filepath = os.path.join(root, filename)
                            process_file(filepath, filename)
                else:
                    # Single file
                    process_file(f.path, f.basename)

            # --- 4. Pack and Transfer ---
            
            # Archive path: Store OUTSIDE temp_root to avoid "file changed as we read it"
            timestamp = int(time.time())
            archive_name = f"download_{timestamp}.tar.gz"
            archive_path = os.path.join("/tmp", archive_name)
            
            # Command: 
            # 1. cd to temp_root
            # 2. tar with -h (dereference symlinks) to archive_path
            # 3. scp to remote
            # 4. clean up
            cmd = (
                f"cd {shlex.quote(temp_root)} && "
                f"tar -czhf {shlex.quote(archive_path)} . && "
                f"scp -P {port} -o StrictHostKeyChecking=no -o ConnectTimeout=10 {shlex.quote(archive_path)} {dest} && "
                f"rm {shlex.quote(archive_path)} && "
                f"rm -rf {shlex.quote(temp_root)}"
            )

            # Execute interactively (flags='w') to allow password input if keys aren't set
            # Change to self.fm.execute_command(cmd) for background execution if keys are set
            self.fm.execute_command(cmd, flags='w')

        except Exception as e:
            self.fm.notify(f"Error: {e}", bad=True)
            if os.path.exists(temp_root):
                shutil.rmtree(temp_root)


# =============================================================================
# Feature 2: Keyword Priority Sort
# =============================================================================

PRIORITY_KEYWORDS = []

def ml_sort_algorithm(file_obj):
    """Sort: Keywords float to top."""
    basename = file_obj.basename.lower()
    for index, keyword in enumerate(PRIORITY_KEYWORDS):
        if keyword.lower() in basename:
            return (index, basename)
    return (999, basename)

Directory.sort_dict['priority'] = ml_sort_algorithm

class priority(Command):
    """
    :priority <kw1> [kw2] ...
    Set priority keywords. Run without args to clear.
    """
    def execute(self):
        global PRIORITY_KEYWORDS
        keywords = self.args[1:]
        
        if not keywords:
            PRIORITY_KEYWORDS = []
            self.fm.notify("Priority cleared.")
        else:
            PRIORITY_KEYWORDS = keywords
            self.fm.notify(f"Priority: {', '.join(keywords)}")
            self.fm.execute_console("set sort=priority")
        
        self.fm.reload_cwd()

    def tab(self, tabnum):
        return ["priority .pth .ckpt", "priority best_ last_", "priority error"]


# =============================================================================
# Feature 3: Date Prefix Sort (Newest First)
# =============================================================================

def date_prefix_sort_algorithm(file_obj):
    """Sort: YYYYMMDD_ prefix, Newest First."""
    basename = file_obj.basename
    if len(basename) >= 9 and basename[8] == '_' and basename[:8].isdigit():
        try:
            date_num = int(basename[:8])
            return (0, -date_num, basename) # Negative for descending sort
        except ValueError:
            pass
    return (1, 0, basename)

Directory.sort_dict['date_prefix'] = date_prefix_sort_algorithm

class sort_date(Command):
    """:sort_date - Sort by date prefix (Newest First)."""
    def execute(self):
        self.fm.notify("Sort: Date Prefix (Newest First)")
        self.fm.execute_console("set sort=date_prefix")
        self.fm.reload_cwd()


# =============================================================================
# Feature 4: Select by Date
# =============================================================================

class mark_date(Command):
    """:mark_date [date] - Select files by date prefix (default: today)."""
    def execute(self):
        target_str = self.arg(1)
        if not target_str or target_str.lower() == 'today':
            target_str = datetime.now().strftime("%Y%m%d")
            
        self.fm.notify(f"Marking date: {target_str} ...")
        self.fm.execute_console("mark all=False")
        
        cwd = self.fm.thisdir
        count = 0
        for f in cwd.files:
            if f.basename.startswith(target_str):
                cwd.mark_item(f, True)
                count += 1
                
        self.fm.notify(f"Marked {count} files.")
        self.fm.ui.redraw_window()
