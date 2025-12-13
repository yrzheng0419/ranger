<div align="left">
<a href="https://ranger.fm/">
<img src="https://ranger.fm/ranger_logo.png" width="200">
</a>

## 基於 Ranger 的模型研究加速系統

本專案以開源終端機檔案管理器 **Ranger** 為基礎，
針對機器學習 / 深度學習研究流程中常見的檔案管理、資料集處理與結果檢視需求，
設計並實作一套 **模型研究加速系統**。

- Original Project (Ranger): https://github.com/ranger/ranger

---

## 專案介紹
Ranger 是一套以 Python 撰寫、支援 Vim-like 鍵盤操作的終端機檔案管理器，
可透過多欄式介面快速瀏覽目錄結構，並支援檔案預覽與高度客製化。

在實驗室實際研究情境中，我們發現研究生常需要反覆進行：
- 資料集整理與重新命名
- 訓練 / 驗證 / 測試資料切分
- 訓練結果版本管理
- 快速查看 CSV、PDF 等實驗輸出
- 將 VM 中的結果下載並分類到本地端

若僅使用傳統 CLI 指令或 GUI 工具，操作繁瑣且容易出錯。
因此本專案在 Ranger 上新增多項指令與預覽功能，
讓研究生能在終端機內完成完整的模型研究流程。

---

## 使用情境與目標
- 不熟悉 Linux 指令的研究者：降低學習門檻、減少指令數量
- 需要大量實驗的研究者：加速資料處理與模型訓練流程
- 模型研究後期：強化版本控制、提升實驗可重現性
- 競賽與論文實驗：快速測試不同資料集與設定

---

## 系統功能

### 1. 資料處理與訓練前置作業
#### (1️) 批量加入日期前綴
為指定資料夾中的所有檔案名稱加上日期前綴（格式：`YYYYMMDD_`），方便依時間追蹤和管理檔案版本。
- 語法：`:add_date_prefix <directory> [falgs]`
- 參數：`-r` 或 `--recursive` 遞迴處理所有子資料夾中的檔案

#### (2) 資料集檔案編號
將資料夾中的所有檔案依序重新命名為 8 位數編號（格式：`00000001.ext`, `00000002.ext`），解決亂碼檔名問題，便於實驗記錄和追蹤。
- 語法：:`dataset_number <directory>`
- 限制：資料夾內不可包含子資料夾（若包含則返回錯誤)

#### (3) YOLO 格式資料集切分
將原始資料集依指定比例切分為訓練集/驗證集/測試集，並自動轉換為 YOLO 格式，支援分類、物件偵測、實例分割三種任務類型。
- 語法：`dataset_split <directory> <x:y:z> <-c|-o|-s> [flags]`
- 參數：
  - `<x:y:z>`：訓練集:驗證集:測試集的比例（例如 7:2:1）
  - `-c`：分類任務 (Classification)
  - `-o`：物件偵測任務 (Object Detection)
  - `-s`：實例分割任務 (Instance Segmentation)
  - `-d <true|false>`：是否加入日期前綴（預設 true），格式：YYYYMMDD_原資料集名稱

### 2. 檔案預覽
#### (1) CSV 檔預覽
Ranger 提供 TXT、CSV 等多種檔案的預覽介面，不過預設的 CSV 預覽不易閱讀，因此改以 pandas Dataframe 提升可讀性，並增加全螢幕預覽模式。
- 以滑鼠點選想要預覽的 CSV 檔即可在右邊欄進行預覽。
- 語法：`,c`，點選想要預覽的 CSV 檔後，鍵入此快捷鍵即可進行全頁預覽。

### 3. 本地下載與分類管理
#### (1) 遠端傳輸
透過 SSH Reverse Tunnel 將 VM 檔案下載至本地，並自動分類。為確保連線穩定，請強制指定 IPv4 Loopback： `ssh -R2222:127.0.0.1:22 user@vm-ip`。
- 語法: :`ssh_download <user@host:path> [flags]`
- 參數 :
  - `-e` : 依 副檔名 (Extension) 分類 (e.g., `jpg/`, `logs/`)
  - `-d` : 依 日期 (Date) 分類 (e.g., `2025-12/`)
  - `-s` <char> : 依 前綴分隔符 (Separator) 分類 (e.g., `ProjectA_ `-> `ProjectA/`)

#### (2) 優先排序
動態調整檔案排序權重，解決訓練目錄檔案雜亂問題。
- Plugin: `ml_priority`
- 指令:
  - `:priority <kw1> [kw2]`: 置頂含有關鍵字的檔案 (e.g., `:priority best .pth`)
  - `:priority`: 清除篩選，恢復預設。

#### (3) 日期管理
針對 `YYYYMMDD_` 格式的檔案進行管理。
- Plugin: `ml_priority` (整合模組)
- 指令
  - :`sort_date:` 切換為 日期前綴排序 (由新到舊)，忽略檔名其餘部分。
  - :`mark_date [date]:` 選取特定日期的檔案 (預設 `today`)，方便批次操作。

---

## 環境需求
- 作業系統：Linux
- 必要套件：
  - `pip install pandas`
  - `sudo apt install poppler-utils` (PDF 預覽)

## References
- Ranger: https://github.com/ranger/ranger
- pandas: https://pandas.pydata.org/

---

# **The original ranger README is preserved below.**

Ranger 1.9.4
============

[![Python lints and tests](https://github.com/ranger/ranger/actions/workflows/python.yml/badge.svg)](https://github.com/ranger/ranger/actions/workflows/python.yml)
<a href="https://repology.org/metapackage/ranger/versions"><img src="https://repology.org/badge/latest-versions/ranger.svg" alt="latest packaged version(s)"></a>
[![Donate via Liberapay](https://img.shields.io/liberapay/patrons/ranger)](https://liberapay.com/ranger)
</div>

Ranger is a console file manager with VI key bindings.  It provides a
minimalistic and nice curses interface with a view on the directory hierarchy.
It ships with `rifle`, a file launcher that is good at automatically finding
out which program to use for what file type.

![screenshot](https://raw.githubusercontent.com/ranger/ranger-assets/master/screenshots/screenshot.png)

For `mc` aficionados there's also the multi-pane viewmode.

<p>
<img src="https://raw.githubusercontent.com/ranger/ranger-assets/master/screenshots/twopane.png" alt="two panes" width="49%" />
<img src="https://raw.githubusercontent.com/ranger/ranger-assets/master/screenshots/multipane.png" alt="multiple panes" width="49%" />
</p>

This file describes ranger and how to get it to run.  For instructions on the
usage, please read the man page (`man ranger` in a terminal).  See `HACKING.md`
for development-specific information.

For configuration, check the files in `ranger/config/` or copy the
default config to `~/.config/ranger` with `ranger --copy-config`
(see [instructions](#getting-started)).

The `examples/` directory contains several scripts and plugins that demonstrate how
ranger can be extended or combined with other programs.  These files can be
found in the git repository or in `/usr/share/doc/ranger`.

A note to packagers: Versions meant for packaging are listed in the changelog
on the website.


About
-----
* Authors:     see `AUTHORS` file
* License:     GNU General Public License Version 3
* Website:     https://ranger.fm/
* Download:    https://ranger.fm/ranger-stable.tar.gz
* Bug reports: https://github.com/ranger/ranger/issues
* git clone    https://github.com/ranger/ranger.git


Design Goals
------------
* An easily maintainable file manager in a high level language
* A quick way to switch directories and browse the file system
* Keep it small but useful, do one thing and do it well
* Console-based, with smooth integration into the unix shell


Features
--------
* UTF-8 Support  (if your Python copy supports it)
* Multi-column display
* Preview of the selected file/directory
* Common file operations (create/chmod/copy/delete/...)
* Renaming multiple files at once
* VIM-like console and hotkeys
* Automatically determine file types and run them with correct programs
* Change the directory of your shell after exiting ranger
* Tabs, bookmarks, mouse support...


Dependencies
------------
* Python (`>=2.6` or `>=3.1`) with the `curses` module
  and (optionally) wide-unicode support
* A pager (`less` by default)

### Optional dependencies

For general usage:

* `file` for determining file types
* `chardet` (Python package) for improved encoding detection of text files
* `sudo` to use the "run as root" feature
* `python-bidi` (Python package) to display right-to-left file names correctly
  (Hebrew, Arabic)

For enhanced file previews (with `scope.sh`):

* `img2txt` (from `caca-utils`) for ASCII-art image previews
* `w3mimgdisplay`, `ueberzug`, `mpv`, `iTerm2`, `kitty` (or other terminal supporting the Kitty graphics protocol), `terminology` or `urxvt` for image previews
* `convert` (from `imagemagick`) to auto-rotate images and for image previews
* `rsvg-convert` (from [`librsvg`](https://wiki.gnome.org/Projects/LibRsvg))
  for SVG previews
* `ffmpeg`, or `ffmpegthumbnailer` for video thumbnails
* `highlight`, `bat` or `pygmentize` for syntax highlighting of code
* `atool`, `bsdtar`, `unrar` and/or `7zz` to preview archives
* `bsdtar`, `tar`, `unrar`, `unzip` and/or `zipinfo` (and `sed`) to preview
  archives as their first image
* `lynx`, `w3m` or `elinks` to preview html pages
* `pdftotext` or `mutool` (and `fmt`) for textual `pdf` previews, `pdftoppm` to
  preview as image
* `djvutxt` for textual DjVu previews, `ddjvu` to preview as image
* `calibre` or `epub-thumbnailer` for image previews of ebooks
* `transmission-show` for viewing BitTorrent information
* `mediainfo` or `exiftool` for viewing information about media files
* `odt2txt` for OpenDocument text files (`odt`, `ods`, `odp` and `sxw`)
* `python` or `jq` for JSON files
* `sqlite3` for listing tables in SQLite database (and optionally `sqlite-utils` for fancier box drawing.)
* `jupyter nbconvert` for Jupyter Notebooks
* `fontimage` for font previews
* `openscad` for 3D model previews (`stl`, `off`, `dxf`, `scad`, `csg`)
* `draw.io` for [draw.io](https://app.diagrams.net/) diagram previews
  (`drawio` extension)

Installing
----------
Use the package manager of your operating system to install ranger.
You can also install ranger through PyPI: `pip install ranger-fm`.
However, it is recommended to use [`pipx`](https://pypa.github.io/pipx/) instead
(to benefit from isolated environments). Use
`pipx run --spec ranger-fm ranger` to install and run ranger in one step.

<details>
  <summary>
    Check current version:
    <sub>
      <a href="https://repology.org/metapackage/ranger/versions">
        <img src="https://repology.org/badge/tiny-repos/ranger.svg" alt="Packaging status">
      </a>
    </sub>
  </summary>
  <a href="https://repology.org/metapackage/ranger/versions">
    <img src="https://repology.org/badge/vertical-allrepos/ranger.svg" alt="Packaging status">
  </a>
</details>

### Installing from a clone
Note that you don't *have* to install ranger; you can simply run `ranger.py`.

To install ranger manually:
```
sudo make install
```

This translates roughly to:
```
sudo python setup.py install --optimize=1 --record=install_log.txt
```

This also saves a list of all installed files to `install_log.txt`, which you can
use to uninstall ranger.


Getting Started
---------------
After starting ranger, you can use the Arrow Keys or `h` `j` `k` `l` to
navigate, `Enter` to open a file or `q` to quit.  The third column shows a
preview of the current file.  The second is the main column and the first shows
the parent directory.

Ranger can automatically copy default configuration files to `~/.config/ranger`
if you run it with the switch `--copy-config=( rc | scope | ... | all )`.
See `ranger --help` for a description of that switch.  Also check
`ranger/config/` for the default configuration.


Going Further
---------------
* To get the most out of ranger, read the [Official User Guide](https://github.com/ranger/ranger/wiki/Official-user-guide).
* For frequently asked questions, see the [FAQ](https://github.com/ranger/ranger/wiki/FAQ%3A-Frequently-Asked-Questions).
* For more information on customization, see the [wiki](https://github.com/ranger/ranger/wiki).


Community
---------------
For help, support, or if you just want to hang out with us, you can find us here:
* **IRC**: channel **#ranger** on [Libera.Chat](https://libera.chat/guides/connect). Don't have an IRC client? Join us via the [webchat](https://web.libera.chat/#ranger)!
* **Reddit**: [r/ranger](https://www.reddit.com/r/ranger/)
