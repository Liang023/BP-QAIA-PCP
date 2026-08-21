from cg.column_independent_set import ColumnIndependentSet

class ColumnPool:
    def __init__(self):
        self.columns=[]

    def addColumn(self,column: ColumnIndependentSet):
        self.columns.append(column)

    def removeColumn(self,column: ColumnIndependentSet):
        self.columns.remove(column)
        
    def copy(self):
        column_pool=ColumnPool()
        column_pool.columns=self.columns.copy()
        return column_pool
    

    
    
    
