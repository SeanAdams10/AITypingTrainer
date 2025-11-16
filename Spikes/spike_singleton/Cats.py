from Setting_file import setting_inst
class Cats:
    def __init__(self):
        self.name = "not yet set"
        self.setting_inst = setting_inst
        self.name = 'set in cat object'
        setting_inst.name = 'modified by cat object'

    


