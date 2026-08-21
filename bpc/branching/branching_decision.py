from cg.column_pool import ColumnPool


class BranchingDecision:
    """分支定价中的分支决策抽象基类。

    具体分支决策需要：
    - 更新辅助图（约束状态）
    - 过滤与该分支约束相违背的列
    """

    def a_graph_update(self, a_graph):
        """将该分支决策作用到辅助图。

        子类需实现：按分支约束修改辅助图。
        """
        pass

    def column_filter(self, column_pool: ColumnPool):
        """根据该分支约束过滤列池。

        子类需实现：移除违反该约束的列；保留人工列以维持可行性。
        """
        pass

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__class__.__name__