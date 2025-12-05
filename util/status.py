# Indicate if function has executed - else message to return to user stored
class Status:
    def __init__(self):
        self.status = False
        self.message = ""

    def set_message(self, message):
        self.message = message

    def set_success(self):
        self.status = True
