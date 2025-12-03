# -----------------------------------------------------------------------------
# Ranger Plugin: ML Priority Sort
# -----------------------------------------------------------------------------
from ranger.api.commands import Command
from ranger.container.directory import Directory

# 儲存優先關鍵字
PRIORITY_KEYWORDS = []

def ml_sort_algorithm(file_obj):
    basename = file_obj.basename.lower()
    for index, keyword in enumerate(PRIORITY_KEYWORDS):
        if keyword.lower() in basename:
            # 權重越低排越前面
            return (index, basename)
    # 沒對到的沉底
    return (999, basename)

# 註冊排序演算法
Directory.sort_dict['priority'] = ml_sort_algorithm

class priority(Command):
    """
    :priority <keyword1> [keyword2] ...
    設定排序優先級。
    """
    def execute(self):
        global PRIORITY_KEYWORDS
        keywords = self.args[1:]
        
        if not keywords:
            PRIORITY_KEYWORDS = []
            self.fm.notify("已清除優先級篩選")
        else:
            PRIORITY_KEYWORDS = keywords
            self.fm.notify(f"優先排序: {', '.join(keywords)}")

        # 強制切換排序模式
        self.fm.execute_console("set sort=priority")
        self.fm.reload_cwd()

    def tab(self, tabnum):
        return ["priority .pth .ckpt", "priority best_ last_", "priority error"]
