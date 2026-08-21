class Edge:
    def __init__(self, source, target, weight=1.0):
        self.source = source
        self.target = target
        
    def __eq__(self, other):
        if not isinstance(other, Edge):
            return False
        return ((self.source == other.source and self.target == other.target) or
                (self.source == other.target and self.target == other.source))
    
    def __hash__(self):
        # Use a tuple of sorted vertex ids to ensure same hash regardless of order
        return hash(tuple(sorted([self.source.id, self.target.id])))
    
    def __str__(self):
        return f"Edge({self.source.id} -> {self.target.id}, weight={self.weight})"
    
    def __repr__(self):
        return f"Edge({self.source.id} -> {self.target.id}, weight={self.weight})"