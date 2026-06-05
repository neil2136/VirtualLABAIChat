import requests

success_msg = 'Your password has been successfully changed'
err_msg1 = 'Your password cannot be changed. Please contact your administrator for assistance'
err_msg2 = 'Please enter a new password'
err_msg3 = 'Your new password does not meet the length, complexity, or history requirements of your domain. Try choosing a different new password'
err_msg4 = 'The entered passwords do not match'
err_msg5 = 'The user name or password that you entered is not valid. Try typing it again'
err_list = [err_msg1, err_msg2, err_msg3, err_msg4, err_msg5]


class LDAPSettings(object):
    def __init__(self, DomainUserName, UserPass, NewUserPass, ConfirmNewUserPass):
        self.DomainUserName = DomainUserName
        self.UserPass = UserPass
        self.NewUserPass = NewUserPass
        self.ConfirmNewUserPass = ConfirmNewUserPass
        self.modify_url = "https://10.103.2.37/RDWeb/Pages/en-US/password.aspx"

    def modifypwd(self):
        modify_res = False
        modify_msg = ''
        data_payload = {
            'DomainUserName': self.DomainUserName,
            'UserPass': self.UserPass,
            'NewUserPass': self.NewUserPass,
            'ConfirmNewUserPass': self.ConfirmNewUserPass,
        }
        output = requests.post(self.modify_url, data=data_payload, verify=False)
        # print(output.text)
        response = output.text
        tr_split = response.split('<tr id')
        for tr in tr_split:
            if 'style="display:"' in tr:
                if success_msg in tr:
                    modify_res = True
                    modify_msg = success_msg
                else:
                    for msg in err_list:
                        if msg in tr:
                            modify_msg = msg
        return modify_res, modify_msg


# if __name__ == '__main__':
#     DomainUserName = 'vlab\lezhang'
#     UserPass = 'password'
#     NewUserPass = 'password2'
#     ConfirmNewUserPass = 'password2'
#     ldap = LDAPSettings(DomainUserName, UserPass, NewUserPass, ConfirmNewUserPass)
#     res = ldap.modifypwd()
#     print(res)
