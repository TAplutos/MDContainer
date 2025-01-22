
class A():
    a = None
    def __init__(self):
        self.b = self.a
    
    def r(self):
        return 1

class B(A):
    def __init__(self):
        self.a = 2
        self.rv = self.r()
        super().__init__()
        print(self.b)

A()
B()