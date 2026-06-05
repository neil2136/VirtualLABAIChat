import pexpect

def try_ssh_login(ip, username, password):

    child = pexpect.spawn('ssh %s@%s' % (username, ip), timeout=3)
    ssh_newkey = 'Are you sure you want to continue connecting'
    index = child.expect(['Connection refused', ssh_newkey, 'password:', pexpect.TIMEOUT])
    if index == 0:
        print('ERROR: ssh was be Connection refused !')
        return child, 'refused'
    elif index == 1:
        child.sendline('yes')
        child.expect(password)
        a = child.expect([pexpect.TIMEOUT, 'password'])
        if a == 0:
            print('SSH could not login. ERROR: %s' % child.before.decode())
            return child, None
    elif index == 2:
        child.sendline(password)
        b = child.expect(['$', 'denied',  pexpect.TIMEOUT])
        if b == 0:
            print('SSH login succdifefully !')
            return child, 'ok'
        elif b == 1:
            print('SSH could not login. Permission denied ERROR')
            return child, 'denied'
        elif b == 2:
            print('SSH could not login. EOF or Timeout ERROR')
            return child, 'error'
    elif index == 3:
        print('SSH could not login : EOF or Timeout ERROR')
        return child, 'error'

def RestartAdapter(ip, username, password):
    child, msg = try_ssh_login(ip, username, password)
    child.sendline('su')
    child.expect('Password:')
    child.sendline('password')
    child.expect('#')
    child.sendline('ip link set ens160 down')
    child.expect('#')
    child.sendline('ip link set ens160 up')
    child.expect('#')
    child.sendline('exit')
