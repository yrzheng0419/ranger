#!/usr/bin/env python3
import sys
from shutil import get_terminal_size

try:
    import pandas as pd
except ImportError:
    print("pandas not installed (pip install pandas)", file=sys.stderr)
    sys.exit(0)

args = sys.argv[1:]
if not args:
    sys.exit(0)

# 是否是全頁模式 (--full)
full = False
if args[0] == "--full":
    full = True
    if len(args) < 2:
        sys.exit(0)
    path = args[1]
else:
    path = args[0]

# 控制輸出寬度
width, height = get_terminal_size((80, 24))

# 行數設定：預設只看前 30 行；全頁模式就不限制
nrows = None if full else 30

try:
    df = pd.read_csv(path, nrows=nrows)
except Exception as e:
    print(f"[CSV preview error] {e}")
    sys.exit(0)

with pd.option_context(
    "display.max_rows", None if full else 30,
    "display.max_columns", 10,
    "display.width", width,
    "display.max_colwidth", 20,
    "display.show_dimensions", False
):
    print(df.to_string(index=False))
