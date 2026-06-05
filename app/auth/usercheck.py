from werkzeug.security import check_password_hash

class UserValid():

    def __init__(self, fullname, email, svname):
        self.fullname = fullname
        self.email = email
        self.svname = svname

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.fullname

    def ping(self):
        return True
    def confirmed(self):
        return True

    @staticmethod
    def validate_login(password_hash, password):
        return check_password_hash(password_hash, password)