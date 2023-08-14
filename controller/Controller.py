class Controller:
    def __init__(self):
        self.db = None

    def set_db(self, db):
        self.db = db
    
    def get_db(self):
        return self.db