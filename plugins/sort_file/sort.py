# -----------------------------------------------------------------------------
# Ranger Plugin: ML Priority Sort
# Description: Sort files based on user-defined dynamic priority keywords.
# Ideal for Machine Learning workflows to float .pth, .ckpt, or 'best_' to top.
# -----------------------------------------------------------------------------

from ranger.api.commands import Command
from ranger.container.directory import Directory

# 這是用來儲存當前使用者設定的「優先關鍵字列表」
# 例如: ['best', '.pth', 'error']
PRIORITY_KEYWORDS = []

def ml_sort_algorithm(file_obj):
    """
    自訂排序演算法：
    檢查檔名是否包含關鍵字。
    如果包含第一個關鍵字 -> 分數 0 (最上面)
    如果包含第二個關鍵字 -> 分數 1
    ...
    都不包含 -> 分數 999 (沉底)
    最後再依據檔名做次級排序 (讓同類型的檔案保持整齊)
    """
    basename = file_obj.basename.lower()
    
    # 遍歷優先列表，找到匹配的關鍵字就回傳對應的索引值 (Index)
    for index, keyword in enumerate(PRIORITY_KEYWORDS):
        if keyword.lower() in basename:
            # 回傳 (權重, 檔名) Tuple
            # 這樣 Ranger 會先比權重(小者在先)，權重一樣再比檔名
            return (index, basename)
    
    # 如果都不匹配，給一個很大的權重 (999)，讓它沉到最下面
    return (999, basename)

# 註冊這個排序演算法到 Ranger
# 名稱叫做 'priority'
Directory.sort_dict['priority'] = ml_sort_algorithm

class priority(Command):
    """
    :priority <keyword1> [keyword2] ...
    
    設定排序優先級。檔案名稱包含 keyword1 的會排在最上面，
    包含 keyword2 的排第二... 以此類推。
    
    不加參數則清除優先級設定，恢復預設排序。
    
    Examples:
    :priority .pth .ckpt    (把模型檔排在最上面)
    :priority best_ .json   (把 best_ 開頭的檔案和 json 排前面)
    :priority error         (把有 error 字眼的 log 撈出來)
    """

    def execute(self):
        global PRIORITY_KEYWORDS
        
        # 1. 讀取使用者輸入的關鍵字
        # self.args[1:] 代表指令後面的所有參數
        keywords = self.args[1:]
        
        if not keywords:
            PRIORITY_KEYWORDS = []
            self.fm.notify("已清除優先級篩選 (回復預設)")
        else:
            PRIORITY_KEYWORDS = keywords
            keyword_str = ", ".join(keywords)
            self.fm.notify(f"目前排序優先級: {keyword_str}")

        # 2. 強制 Ranger 切換到我們自訂的 'priority' 排序模式
        self.fm.execute_console("set sort=priority")
        
        # 3. 重新載入當前目錄以刷新排序
        self.fm.reload_cwd()

    def tab(self, tabnum):
        # 按 Tab 的時候提供一些 ML 常用的補全建議 (貼心功能)
        defaults = [
            "priority .pth .ckpt", 
            "priority best_ last_", 
            "priority .log error", 
            "priority .png .jpg"
        ]
        return defaults
