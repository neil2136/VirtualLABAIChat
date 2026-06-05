#!/usr/bin/env python
import pexpect, random, os, re, sys
from random import Random
from flask import current_app, flash
from flask_login import current_user
import time
fw_ip = '10.8.104.69'
fw_user = 'admin'
fw_pwd = 'password'
loginprompt = '[$#>:]'

def random_word(randomlength=4):
    str = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    length = len(chars) - 1
    random = Random()
    for i in range(randomlength):
        str += chars[random.randint(0, length)]
    return str

def increased_ipv4(aoip, times):
    ip_pool = {}
    cont, i, j, k = 1, 1, 1, 1
    tmp_ip = aoip.split('.')
    a = tmp_ip[0]
    b = tmp_ip[1]
    c = tmp_ip[2]
    start_ip = int(tmp_ip[-1])
    end_ip = start_ip + int(times)
    #只存在一个子网时，生成子网内ip
    if end_ip//255 == 0:
        for start_ip in range(start_ip, end_ip):
            ip_pool[cont] = a + '.' + b + '.' + c + '.' + str(start_ip)
            cont += 1
    else:
        #形成起始到254的ip
        for start_ip in range(start_ip, 255):
            ip_pool[cont] = a + '.' + b + '.' + c + '.' + str(start_ip)
            cont += 1

        #取254的倍数，形成一个子网的ip
        for j in range(j, (int(times) - cont + 1)//254 + 1):
            if int(c) < 254:
                c = int(c) + 1
                for k in range(k, 255):
                    ip_pool[cont] = str(a) + '.' + str(b) + '.' + str(c) + '.' + str(k)
                    cont += 1
                k = 1
            elif int(c) > 253 and int(b) < 254:
                b = int(b) + 1
                for k in range(k, 255):
                    ip_pool[cont] = str(a) + '.' + str(b) + '.' + str(c) + '.' + str(k)
                    cont += 1
                k = 1
            if int(b) > 253:
                a = int(a) + 1
                for k in range(k, 255):
                    ip_pool[cont] = str(a) + '.' + str(b) + '.' + str(c) + '.' + str(k)
                    cont += 1
                k = 1
        #取余数，形成剩余的ip
        if int(c) < 254:
            c = int(c) + 1
        if int(c) > 253 and int(b) < 254:
            b = int(b) + 1
        if int(b) > 253:
            a = int(a) + 1
        for i in range(i, (int(times) - cont + 1) % 254 + 1):

            ip_pool[cont] = str(a) + '.' + str(b) + '.' + str(c) + '.' + str(i)
            cont += 1
    #print('ip pool-------------%s' % ip_pool)
    #print('cont-------------%s' % cont)
    return ip_pool
#increased_ipv4('66.77.254.253', 999)

def try_ssh_login(ip, username, password):

    child = pexpect.spawn('ssh %s@%s' % (username, ip), timeout=3)
    ssh_newkey = 'Are you sure you want to continue connecting'
    index = child.expect(['Connection refused', '(yes/no/[fingerprint])?', 'password', pexpect.TIMEOUT])
    print('0000000000000000000000000')
    print(child.before.decode())
    # print(child.after.decode())
    if index == 0:
        print('ERROR: ssh was be Connection refused !')
        return child, 'refused'
    elif index == 1:
        child.sendline('yes')
        child.buffer = b''
        a = child.expect([pexpect.TIMEOUT, 'password'])
        print('2222222222222222222222')
        print(child.before.decode())
        # print(child.after.decode())
        if a == 0:
            print('SSH could not login. ERROR: %s' % child.before.decode())
            return child, None
        child.sendline(password)
        child.expect('>')
        return child, 'ok'
    elif index == 2:
        child.sendline(password)
        b = child.expect(['>', 'denied', 'yes:', pexpect.TIMEOUT])
        if b == 0:
            print('SSH login succefully !')
            return child, 'ok'
        elif b == 1:
            print('SSH could not login. Permission denied ERROR')
            return child, 'denied'
        elif b == 2:
            print('Accept The Policy Banner (yes)?')
            child.sendline('yes')
            child.expect('>')
            return child, 'ok'
        elif b == 3:
            print('SSH could not login. EOF or Timeout ERROR')
            return child, 'error'
    elif index == 3:
        print('SSH could not login : EOF or Timeout ERROR')
        return child, 'error'

#try_ssh_login('10.8.105.212', 'admin', 'password')

def ssh_login(ip, username, password):

    child, codes = try_ssh_login(ip, username, password)
    # atexit.register(child)
    child.sendline('con')
    if child.expect([pexpect.TIMEOUT, '#'], timeout=3):
        current_app.logger.warning('[' + current_user.fullname + ']-- Go to FW %s config mode...' % ip)
        pass
    elif child.expect([pexpect.TIMEOUT, 'Do you wish to preempt them'], timeout=3):
        print('FW was be preempt by anther user, Try to force it...')
        current_app.logger.warning(
           '[' + current_user.fullname + ']-- FW was be preempt by anther user, Try to force it...')
        child.sendline('yes')
        child.expect('#')
        current_app.logger.warning('[' + current_user.fullname + ']-- Force FW %s successfully !' % ip)
    return child

'''
def ssh_login(ip, username, password):

    current_app.logger.warning('[' + current_user.fullname + ']-- start login to FW %s ...' % ip)
    child = pexpect.spawn('ssh %s@%s' % (fullname, ip))
    ssh_newkey = 'Are you sure you want to continue connecting'
    i = child.expect([pexpect.TIMEOUT, ssh_newkey, 'password'])
    # if login timeout, print error and end.
    if i == 0:
        print('ERROR!')
        print('SSH could not login. Here is what SSH said:')
        print(child.before.decode())
        return None
    # if ssh have not public key, just accept it.
    elif i == 1:
        child.sendline('yes')
        child.expect('password')
        i = child.expect([pexpect.TIMEOUT, 'password'])
        if i == 0:
            print('ERROR!')
            print('SSH could not login. Here is what SSH said:')
            print(child.before.decode())
            return None
    child.sendline(password)
    child.expect('>')
    #print(child.before.decode())
    current_app.logger.warning('[' + current_user.username + ']-- login to FW %s successfully !' % ip)
    child.sendline('con')
    if child.expect([pexpect.TIMEOUT, '#'], timeout=1):
        current_app.logger.warning('[' + current_user.username + ']-- Go to FW %s config mode...' % ip)
        return child
    elif child.expect([pexpect.TIMEOUT, 'Do you wish to preempt them'], timeout=1):
        print('FW was be preempt by anther user, Try to force it...')
        current_app.logger.warning('[' + current_user.username + ']-- FW was be preempt by anther user, Try to force it...')
        child.sendline('yes')
        child.expect('#')
        current_app.logger.warning('[' + current_user.username + ']-- Force FW %s successfully !' % ip)
        return child
'''
def dynamic_ao(dutip, dutuser, dutpwd, aoname, aozone, aoip, times):
    cont = 0
    ip_pool = increased_ipv4(aoip, times)
    current_app.logger.warning('[' + current_user.fullname + ']--start login target device: %s' % dutip)
    self = ssh_login(dutip, dutuser, dutpwd)
    if int(times) < 101:
        for n in range(0, int(times) // 10):
            for m in range(0, 10):
                cont += 1
                self.sendline(
                    'address-object ipv4 auto_%s_%s host %s zone %s' % (aoname, cont, ip_pool[cont], aozone))
                self.expect('#')
                current_app.logger.warning('[' + current_user.fullname + ']--add AO number-------%s' % cont)
            self.sendline('commit')
            self.expect('#')
            current_app.logger.warning('[' + current_user.fullname + ']--add %s AO numbers seccessful !' % cont)
        current_app.logger.warning('[' + current_user.fullname + ']--add %s AO numbers seccessful !' % cont)
        for cont in range(cont, int(times)):
            cont += 1
            self.sendline(
                'address-object ipv4 auto_%s_%s host %s zone %s' % (aoname, cont, ip_pool[cont], aozone))
            self.expect('#')
            self.sendline('commit')
            self.expect('#')
            current_app.logger.warning('[' + current_user.fullname + ']--add AO number-------%s' % cont)
        current_app.logger.warning('[' + current_user.fullname + ']--end of add, total add AO---------------%s' % cont)
    elif int(times) > 101 and int(times) < 1000:
        for n in range(0, int(times) // 100):
            for m in range(1, 101):
                cont += 1
                self.sendline(
                    'address-object ipv4 auto_%s_%s host %s zone %s' % (aoname, cont, ip_pool[cont], aozone))
                self.expect('#')
                current_app.logger.warning('[' + current_user.fullname + ']--add AO number-------%s' % cont)
            self.sendline('commit')
            self.expect('#')
            current_app.logger.warning('[' + current_user.fullname + ']--add %s AO numbers seccessful !' % cont)
        current_app.logger.warning('[' + current_user.fullname + ']--add %s AO numbers seccessful !' % cont)
        for i in range(0, int(times) // 10 % 10):
            for j in range(0, 10):
                cont += 1
                self.sendline(
                    'address-object ipv4 auto_%s_%s host %s zone %s' % (aoname, cont, ip_pool[cont], aozone))
                self.expect('#')
                current_app.logger.warning('[' + current_user.fullname + ']--add AO number-------%s' % cont)
            current_app.logger.warning('[' + current_user.fullname + ']--add %s AO numbers seccessful !' % cont)
            self.sendline('commit')
            self.expect('#')
        current_app.logger.warning('[' + current_user.fullname + ']--add %s AO numbers seccessful !' % cont)
        for cont in range(cont, int(times)):
            cont += 1
            self.sendline(
                'address-object ipv4 auto_%s_%s host %s zone %s' % (aoname, cont, ip_pool[cont], aozone))
            self.expect('#')
            self.sendline('commit')
            self.expect('#')
            current_app.logger.warning('[' + current_user.fullname + ']--add %s AO numbers seccessful !' % cont)
        current_app.logger.warning('[' + current_user.fullname + ']--add %s AO numbers seccessful !' % cont)
        current_app.logger.warning('[' + current_user.fullname + ']--end of add, total add AO---------------%s' % cont)
    else:
        flash('input error...')

    exit_login(self)
    return cont

def add_address_objects(dutip, dutuser, dutpwd, aoname, aozone, aoip, times):
    current_app.logger.warning('[' + current_user.fullname + ']--start add address-objects ...')
    if aoname == 'auto':
        aoname = random_word()
        current_app.logger.warning('[' + current_user.fullname + ']--Determine that aoname is auto and start generating random AO names...')
        cont = dynamic_ao(dutip, dutuser, dutpwd, aoname, aozone, aoip, times)
    else:
        cont = dynamic_ao(dutip, dutuser, dutpwd, aoname, aozone, aoip, times)
    return cont

def unidigit_add_address_gp(self, count_gp, agname, agmemberof, times):
    for cont in range(count_gp, int(times)):
        count_gp += 1
        self.sendline('address-group ipv4 auto_%s_%s' % (agname, count_gp))
        self.expect('#')
        self.sendline('address-group ipv4 %s' % agmemberof)
        self.expect('#')
        self.sendline('commit')
        self.expect('#')
        #print(self.before.decode())
        if len(re.findall('Too many users', self.before.decode())) == 0:
            current_app.logger.warning(
                '[' + current_user.fullname + ']--add address group: auto_%s_%s@auto.com seccessful !' % (agname, count_gp))
            self.sendline('exit')
            self.expect('#')
        else:
            current_app.logger.warning(
                '[' + current_user.fullname + ']--Error: Creating auto_%s_%s: add Failed: The ability to add address Groups is at its limit!!! ' % (
                    agname, count_gp))
            exit_login(self)
            return count_gp
    return count_gp

def tendigit_add_address_gp(self, count_gp, agname, agmemberof, tag):

    for m in range(0, 10):
        count_gp += 1
        self.sendline('address-group ipv4 auto_%s_%s' % (agname, count_gp))
        self.expect('#')
        self.sendline('address-group ipv4 %s' % agmemberof)
        self.expect('#')
        self.sendline('exit')
        self.expect('#')
        current_app.logger.warning('[' + current_user.fullname + ']--add address group-------%s' % count_gp)
    self.sendline('commit')
    self.expect('#')
    if len(re.findall('Too many users', self.before.decode())) == 0:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--add address group: auto_%s_%s@auto.com seccessful !' % (agname, count_gp))
        tag = 0
    else:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--Error: Creating auto_%s_%s: add Failed: The ability to add address Groups is at its limit!!! ' % (
                agname, count_gp))
    return count_gp, tag

def centile_add_address_gp(self, count_gp, agname, agmemberof, tag):
    for j in range(1, 101):
        count_gp += 1
        self.sendline('address-group ipv4 auto_%s_%s' % (agname, count_gp))
        self.expect('#')
        self.sendline('address-group ipv4 %s' % agmemberof)
        self.expect('#')
        self.sendline('exit')
        self.expect('#')
        current_app.logger.warning('[' + current_user.fullname + ']--add address group-------%s' % count_gp)
    self.sendline('commit')
    self.expect('#')
    if len(re.findall('Too many users', self.before.decode())) == 0:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--add address group: auto_%s_%s@auto.com seccessful !' % (agname, count_gp))
        tag = 0
    else:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--Error: Creating auto_%s_%s: add Failed: The ability to add address Groups is at its limit!!! ' % (
                agname, count_gp))
        tag = 1
    return count_gp, tag

def dynamic_address_group(dutip, dutuser, dutpwd, agname, agmemberof, times):
    count_gp = 0
    tag = 0
    self = ssh_login(dutip, dutuser, dutpwd)
    if int(times) < 101:
        #add centile digit Local Groups
        for n in range(0, int(times) // 10):
            count_gp, tag = tendigit_add_address_gp(self, count_gp, agname, agmemberof, tag)
            if tag == 1:
                flash('Failed: adding address group are reached limit!!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count_gp
        #add the single digit Address Groups
        count_gp = unidigit_add_address_gp(self, count_gp, agname, agmemberof, times)
        current_app.logger.warning('[' + current_user.fullname + ']--end of add, total add address groups---------------%s' % count_gp)

    elif int(times) > 101 and int(times) < 1000:
        # add tens digit Address Groups
        for n in range(0, int(times) // 100):
            count_gp, tag = centile_add_address_gp(self, count_gp, agname, agmemberof, tag)
            if tag == 1:
                flash('Failed: adding address groups are reached limit!!! Please try to use ten digit times(10-99).')
                exit_login(self)
                return count_gp
        # add tens digit address Groups
        for i in range(0, int(times) // 10 % 10):
            count_gp, tag = tendigit_add_address_gp(self, count_gp, agname, agmemberof, tag)
            if tag == 1:
                flash('Failed: adding address groups are reached limit!!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count_gp
        # add the single digit address Groups
        count_gp = unidigit_add_address_gp(self, count_gp, agname, agmemberof, times)
        current_app.logger.warning(
            '[' + current_user.fullname + ']--end of add, total add address groups---------------%s' % count_gp)
    else:
        flash('input error...')

    exit_login(self)
    return count_gp

def add_address_groups(dutip, dutuser, dutpwd, agname, agmemberof, times):
    current_app.logger.warning('[' + current_user.fullname + ']--start add address groups ...')
    if agname == 'auto':
        agname = random_word()
        current_app.logger.warning('[' + current_user.fullname + ']--Determine that localname is auto and start generating random names...')
        cont = dynamic_address_group(dutip, dutuser, dutpwd, agname, agmemberof, times)
    else:
        cont = dynamic_address_group(dutip, dutuser, dutpwd, agname, agmemberof, times)
    return cont

def check_entries(self):

    if len(re.findall('Too many users', self.before.decode())) == 0:
        return 0

    else:
        #flash('Error: Creating auto_%s_%s: Add User Failed: The ability to add Local Users is at its limit!!!' % (localname, count_local))
        exit_login(self)
        return 1

def unidigit_add_local_user(self, count_local, localname, localpwd, memberof, times):

    for cont in range(count_local, int(times)):
        count_local += 1
        self.sendline(
            'user auto_%s_%s password %s member-of %s' % (localname, count_local, localpwd, memberof))
        self.expect('#')
        # print('user auto_%s_%s password %s member-of %s' % (localname, count_local, localpwd, memberof))
        self.sendline('commit')
        self.expect('#')

        if len(re.findall('Too many users', self.before.decode())) == 0:
            current_app.logger.warning(
                '[' + current_user.fullname + ']--add local user: auto_%s_%s seccessful !' % (localname, count_local))

        else:
            current_app.logger.warning(
                '[' + current_user.fullname + ']--Error: Creating auto_%s_%s: Add User Failed: The maximum number of Local Users has been added !!!' % (
                    localname, count_local))
            exit_login(self)
            return count_local
    return count_local

def tendigit_add_local_user(self, count_local, localname, localpwd, memberof, tag):

    for m in range(0, 10):
        count_local += 1
        self.sendline(
            'user auto_%s_%s password %s member-of %s' % (localname, count_local, localpwd, memberof))
        self.expect('#')
        current_app.logger.warning('[' + current_user.fullname + ']--add local user number-------%s' % count_local)
    self.sendline('commit')
    self.expect('#')
    if len(re.findall('Too many users', self.before.decode())) == 0:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--add local user: auto_%s_%s seccessful !' % (localname, count_local))
        tag = 0
    else:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--Error: Creating auto_%s_%s: Add User Failed: The maximum number of Local Users has been added !!! ' % (
                localname, count_local))
    return count_local, tag

def centile_add_local_user(self, count_local, localname, localpwd, memberof, tag):
    for m in range(1, 101):
        count_local += 1
        self.sendline(
            'user auto_%s_%s password %s member-of %s' % (localname, count_local, localpwd, memberof))
        self.expect('#')
        current_app.logger.warning('[' + current_user.fullname + ']--add local user number-------%s' % count_local)
    self.sendline('commit')
    self.expect('#')
    if len(re.findall('Too many users', self.before.decode())) == 0:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--add local user: auto_%s_%s seccessful !' % (localname, count_local))
        tag = 0
    else:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--Error: Creating auto_%s_%s: Add User Failed: The maximum number of Local Users has been added !!! ' % (
                localname, count_local))
        tag = 1
    return count_local, tag

def exit_login(self):

    self.sendline('end')
    self.sendline('no')
    self.sendline('exit')
    #self.expect('>')
    current_app.logger.warning('[' + current_user.fullname + ']--exit FW seccessful !')

def dynamic_local_user(dutip, dutuser, dutpwd, localname, localpwd, memberof, times):
    count_local = 0
    tag = 0
    self = ssh_login(dutip, dutuser, dutpwd)
    self.sendline('user local')
    self.expect('#')
    if int(times) < 101:
        #add tens digit Local users
        for n in range(0, int(times) // 10):
            count_local, tag = tendigit_add_local_user(self, count_local, localname, localpwd, memberof, tag)
            if tag == 1:
                flash('Failed: adding local users are reached limit!!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count_local
        #add the single digit Local Users
        count_local = unidigit_add_local_user(self, count_local, localname, localpwd, memberof, times)
        current_app.logger.warning('[' + current_user.fullname + ']--end of add, total add local users---------------%s' % count_local)

    elif int(times) > 101 and int(times) < 1000:
        for n in range(0, int(times) // 100):
            count_local, tag = centile_add_local_user(self, count_local, localname, localpwd, memberof, tag)
            if tag == 1:
                flash('Failed: adding local users are reached limit!!! Please try to use ten digit times(10-99).')
                exit_login(self)
                return count_local
        for i in range(0, int(times) // 10 % 10):
            count_local, tag = tendigit_add_local_user(self, count_local, localname, localpwd, memberof, tag)
            if tag == 1:
                flash('Failed: adding local users are reached limit!!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count_local
            # add the single digit Local Users
        count_local = unidigit_add_local_user(self, count_local, localname, localpwd, memberof, times)
        current_app.logger.warning(
            '[' + current_user.fullname + ']--end of add, total add local users---------------%s' % count_local)
    else:
        flash('input error...')
    exit_login(self)
    return count_local

def add_local_users(dutip, dutuser, dutpwd, localname, localpwd, memberof, times):
    current_app.logger.warning('[' + current_user.fullname + ']--start add local user ...')
    if localname == 'auto':
        localname = random_word()
        current_app.logger.warning('[' + current_user.fullname + ']--Determine that localname is auto and start generating random Local names...')
        cont = dynamic_local_user(dutip, dutuser, dutpwd, localname, localpwd, memberof, times)
    else:
        cont = dynamic_local_user(dutip, dutuser, dutpwd, localname, localpwd, memberof, times)
    return cont

def unidigit_add_local_gp(self, count_gp, gpname, gpmemberof, times):
    for cont in range(count_gp, int(times)):
        count_gp += 1
        self.sendline('group auto_%s_%s domain auto.com' % (gpname, count_gp))
        self.expect('#')
        self.sendline('member %s' % gpmemberof)
        self.expect('#')
        self.sendline('commit')
        self.expect('#')
        #print(self.before.decode())
        if len(re.findall('Too many users', self.before.decode())) == 0:
            current_app.logger.warning(
                '[' + current_user.fullname + ']--add local group: auto_%s_%s@auto.com seccessful !' % (gpname, count_gp))
            self.sendline('exit')
            self.expect('#')
        else:
            current_app.logger.warning(
                '[' + current_user.fullname + ']--Error: Creating auto_%s_%s: add Failed: The ability to add Local Groups is at its limit!!! ' % (
                    gpname, count_gp))
            exit_login(self)
            return count_gp
    return count_gp

def tendigit_add_local_gp(self, count_gp, gpname, gpmemberof, tag):

    for m in range(0, 10):
        count_gp += 1
        self.sendline('group auto_%s_%s domain auto.com' % (gpname, count_gp))
        self.expect('#')
        self.sendline('member %s' % gpmemberof)
        self.expect('#')
        self.sendline('exit')
        self.expect('#')
        current_app.logger.warning('[' + current_user.fullname + ']--add local group-------%s' % count_gp)
    self.sendline('commit')
    self.expect('#')
    if len(re.findall('Too many users', self.before.decode())) == 0:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--add local group: auto_%s_%s@auto.com seccessful !' % (gpname, count_gp))
        tag = 0
    else:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--Error: Creating auto_%s_%s: add Failed: The ability to add Local Groups is at its limit!!! ' % (
                gpname, count_gp))
    return count_gp, tag

def centile_add_local_gp(self, count_gp, gpname, gpmemberof, tag):
    for j in range(1, 101):
        count_gp += 1
        self.sendline('group auto_%s_%s domain auto.com' % (gpname, count_gp))
        self.expect('#')
        self.sendline('member %s' % gpmemberof)
        self.expect('#')
        self.sendline('exit')
        self.expect('#')
        current_app.logger.warning('[' + current_user.fullname + ']--add local group-------%s' % count_gp)
    self.sendline('commit')
    self.expect('#')
    if len(re.findall('Too many users', self.before.decode())) == 0:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--add local group: auto_%s_%s@auto.com seccessful !' % (gpname, count_gp))
        tag = 0
    else:
        current_app.logger.warning(
            '[' + current_user.fullname + ']--Error: Creating auto_%s_%s: add Failed: The ability to add Local Groups is at its limit!!! ' % (
                gpname, count_gp))
        tag = 1
    return count_gp, tag

def dynamic_local_group(dutip, dutuser, dutpwd, gpname, gpmemberof, times):
    count_gp = 0
    tag = 0
    self = ssh_login(dutip, dutuser, dutpwd)
    self.sendline('user local')
    self.expect('#')
    if int(times) < 101:
        #add centile digit Local Groups
        for n in range(0, int(times) // 10):
            count_gp, tag = tendigit_add_local_gp(self, count_gp, gpname, gpmemberof, tag)
            if tag == 1:
                flash('Failed: adding local group are reached limit!!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count_gp
        #add the single digit Local Groups
        count_gp = unidigit_add_local_gp(self, count_gp, gpname, gpmemberof, times)
        current_app.logger.warning('[' + current_user.fullname + ']--end of add, total add local groups---------------%s' % count_gp)

    elif int(times) > 101 and int(times) < 1000:
        # add tens digit Local Groups
        for n in range(0, int(times) // 100):
            count_gp, tag = centile_add_local_gp(self, count_gp, gpname, gpmemberof, tag)
            if tag == 1:
                flash('Failed: adding local groups are reached limit!!! Please try to use ten digit times(10-99).')
                exit_login(self)
                return count_gp
        # add tens digit Local Groups
        for i in range(0, int(times) // 10 % 10):
            count_gp, tag = tendigit_add_local_gp(self, count_gp, gpname, gpmemberof, tag)
            if tag == 1:
                flash('Failed: adding local groups are reached limit!!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count_gp
        # add the single digit Local Groups
        count_gp = unidigit_add_local_gp(self, count_gp, gpname, gpmemberof, times)
        current_app.logger.warning(
            '[' + current_user.fullname + ']--end of add, total add local groups---------------%s' % count_gp)
    else:
        flash('input error...')

    exit_login(self)
    return count_gp

def add_local_groups(dutip, dutuser, dutpwd, gpname, gpmemberof, times):
    current_app.logger.warning('[' + current_user.fullname + ']--start add local groups ...')
    if gpname == 'auto':
        gpname = random_word()
        current_app.logger.warning('[' + current_user.fullname + ']--Determine that localname is auto and start generating random names...')
        cont = dynamic_local_group(dutip, dutuser, dutpwd, gpname, gpmemberof, times)
    else:
        cont = dynamic_local_group(dutip, dutuser, dutpwd, gpname, gpmemberof, times)
    return cont

def add_vpn_cmd(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive):
    self.sendline('vpn policy %s auto_%s_%s' % (policytype, vpnname, count))
    self.expect('#')
    self.sendline('gateway primary %s' % primaryip[count])
    self.expect('#')
    self.sendline('auth-method shared-secret')
    self.expect('#')
    self.sendline('shared-secret %s' % sharedsecret)
    self.expect('#')
    self.sendline('exit')
    self.expect('#')
    self.sendline('network local group %s' % localnetwork)
    self.expect('#')
    self.sendline('network remote host %s' % remotenetwork[count])
    self.expect(loginprompt)
    self.sendline('yes')
    self.expect('#')
    self.sendline('%s' % keepalive)
    self.expect('#')
    self.sendline('exit')
    self.expect('#')
    current_app.logger.warning(
        '[' + current_user.fullname + ']--start add the policy -----------> auto_%s_%s !' % (vpnname, count))
    return self

def add_vpn_commit(self, count, vpnname):
    self.sendline('commit')
    self.expect('#')
    strs = self.before.decode()
    end_2_line = strs.split('\r\n')[-2]
    #print(end_2_line)
    #print(end_2_line.find('Maximum Policies'))
    #print(end_2_line.find('overlaps'))
    #if len(re.findall('Maximum Policies', line_2)) or len(re.findall('overlaps', line_2)) == 0:
    if end_2_line.find('Maximum Policies') == -1 and end_2_line.find('overlaps') == -1:
        tag = 0
        current_app.logger.warning(
            '[' + current_user.fullname + ']--add VPN Policy: auto_%s_%s seccessful !' % (vpnname, count))
    else:
        tag = 1
        flash(end_2_line)
        current_app.logger.warning('[' + current_user.fullname + ']--' + end_2_line)
    return self, tag

def unidigit_add_vpn_policy(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive, times):
    for count in range(count, int(times)):
        count += 1
        self = add_vpn_cmd(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive)
        self, tag = add_vpn_commit(self, count, vpnname)
        if tag == 1:
            self.sendline('no address-group ipv4 %s' % remotenetwork[count])
            #self.expect('#')
            return count
    return count

def tendigit_add_vpn_policy(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive):
    tmp_ao = {}
    for m in range(0, 10):
        count += 1
        self = add_vpn_cmd(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork,
                           keepalive)
        tmp_ao[m+1] = remotenetwork[count]
    self, tag = add_vpn_commit(self, count, vpnname)
    if tag == 1:
        for i in range(1, 11):
            self.sendline('no address-group ipv4 %s' % tmp_ao[i])
    return count, tag

def centile_add_vpn_policy(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive):
    tmp_ao = {}
    for j in range(0, 100):
        count += 1
        self = add_vpn_cmd(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork,
                           keepalive)
        tmp_ao[j+1] = remotenetwork[count]

    self, tag = add_vpn_commit(self, count, vpnname)
    if tag == 1:
        for i in range(1, 101):
            self.sendline('no address-group ipv4 %s' % tmp_ao[i])
    return count, tag

def dynamic_vpn_policy(dutip, dutuser, dutpwd, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive, times):
    count = 0
    self = ssh_login(dutip, dutuser, dutpwd)
    primaryip = increased_ipv4(primaryip, times)
    remotenetwork = increased_ipv4(remotenetwork, times)

    if int(times) < 101:
        #add centile digit vpn policies
        for n in range(0, int(times) // 10):
            count, tag = tendigit_add_vpn_policy(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive)
            if tag == 1:
                flash('Failed: vpn policies are reached limit or overlaps !!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count
        #add the single digit vpn policies
        count = unidigit_add_vpn_policy(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive, times)
        current_app.logger.warning('[' + current_user.fullname + ']--end of add, total add vpn policies---------------%s' % count)

    elif int(times) > 101 and int(times) < 1000:
        # add tens digit vpn policies
        for n in range(0, int(times) // 100):
            count, tag = centile_add_vpn_policy(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive)
            if tag == 1:
                flash('Failed: adding vpn policies are reached limit or overlaps!!! Please try to use ten digit times(10-99).')
                exit_login(self)
                return count
        # add tens digit vpn policies
        for i in range(0, int(times) // 10 % 10):
            count, tag = tendigit_add_vpn_policy(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive)
            if tag == 1:
                flash('Failed: adding vpn policies are reached limit!!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count
        # add the single digit vpn policies
        count = unidigit_add_vpn_policy(self, count, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive, times)
        current_app.logger.warning(
            '[' + current_user.fullname + ']--end of add, total add vpn policies---------------%s' % count)
    else:
        flash('input error...')

    exit_login(self)
    return count

def add_vpn_policies(dutip, dutuser, dutpwd, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive, times):
    current_app.logger.warning('[' + current_user.fullname + ']--start add VPN Policies ...')
    if vpnname == 'auto':
        vpnname = random_word()
        current_app.logger.warning('[' + current_user.fullname + ']--Determine that localname is auto and start generating random names...')
        cont = dynamic_vpn_policy(dutip, dutuser, dutpwd, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive, times)
    else:
        cont = dynamic_vpn_policy(dutip, dutuser, dutpwd, policytype, vpnname, primaryip, sharedsecret, localnetwork, remotenetwork, keepalive, times)
    return cont

def add_route_cmd(self, count, routename, interface, metric, source, destination, service):
    self.sendline('route-policy interface %s metric %s source host %s destination host %s service group %s' % (interface, metric, source[count], destination[count], service))
    self.expect(loginprompt)
    self.sendline('yes')
    self.sendline('yes')
    self.expect('#')
    self.sendline('name auto_%s_%s' % (routename, count))
    self.expect('#')
    self.sendline('exit')
    self.expect('#')
    current_app.logger.warning(
        '[' + current_user.fullname + ']--start add the Route policy -----------> auto_%s_%s !' % (routename, count))
    return self

def add_route_commit(self, count, routename):
    self.sendline('commit')
    self.expect('#')
    strs = self.before.decode()
    end_2_line = strs.split('\r\n')[-2]
    print(strs)
    #print(end_2_line.find('Maximum Policies'))
    #print(end_2_line.find('overlaps'))
    #if len(re.findall('Maximum Policies', line_2)) or len(re.findall('overlaps', line_2)) == 0:
    if end_2_line.find('Maximum Policies') == -1 and end_2_line.find('overlaps') == -1 and end_2_line.find('no matching command') == -1:
        tag = 0
        current_app.logger.warning(
            '[' + current_user.fullname + ']--add route Policy: auto_%s_%s seccessful !' % (routename, count))
    else:
        tag = 1
        flash(end_2_line)
        current_app.logger.warning('[' + current_user.fullname + ']--' + end_2_line)
    return self, tag

def unidigit_add_route_policy(self, count, routename, interface, metric, source, destination, service, times):
    for count in range(count, int(times)):
        count += 1
        self = add_route_cmd(self, count, routename, interface, metric, source, destination, service)
        self, tag = add_route_commit(self, count, routename)
        if tag == 1:
            self.sendline('no address-group ipv4 %s' % source[count])
            self.sendline('no address-group ipv4 %s' % destination[count])
            #self.expect('#')
            return count
    return count

def tendigit_add_route_policy(self, count, routename, interface, metric, source, destination, service):
    tmp_ao = {}
    tmp_ao2 = {}
    for m in range(0, 10):
        count += 1
        self = add_route_cmd(self, count, routename, interface, metric, source, destination, service)
        tmp_ao[m+1] = source[count]
        tmp_ao2[m + 1] = destination[count]
    self, tag = add_route_commit(self, count, routename)
    if tag == 1:
        for i in range(1, 11):
            self.sendline('no address-group ipv4 %s' % tmp_ao[i])
            self.sendline('no address-group ipv4 %s' % tmp_ao2[i])
    return count, tag

def centile_add_route_policy(self, count, routename, interface, metric, source, destination, service):
    tmp_ao = {}
    tmp_ao2 = {}
    for j in range(0, 100):
        count += 1
        self = add_route_cmd(self, count, routename, interface, metric, source, destination, service)
        tmp_ao[j+1] = source[count]
        tmp_ao2[j + 1] = destination[count]

    self, tag = add_route_commit(self, count, routename)
    if tag == 1:
        for i in range(1, 101):
            self.sendline('no address-group ipv4 %s' % tmp_ao[i])
            self.sendline('no address-group ipv4 %s' % tmp_ao2[i])
    return count, tag

def dynamic_route_policy(dutip, dutuser, dutpwd, routename, interface, metric, source, destination, service, times):
    count = 0
    self = ssh_login(dutip, dutuser, dutpwd)
    source = increased_ipv4(source, times)
    destination = increased_ipv4(destination, times)

    if int(times) < 101:
        #add centile digit
        for n in range(0, int(times) // 10):
            count, tag = tendigit_add_route_policy(self, count,  routename, interface, metric, source, destination, service)
            if tag == 1:
                flash('Failed: route policies are reached limit or overlaps !!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count
        #add the single digit
        count = unidigit_add_route_policy(self, count,  routename, interface, metric, source, destination, service, times)
        current_app.logger.warning('[' + current_user.fullname + ']--end of add, total add route policies---------------%s' % count)

    elif int(times) > 101 and int(times) < 1000:
        # add tens digit
        for n in range(0, int(times) // 100):
            count, tag = centile_add_route_policy(self, count,  routename, interface, metric, source, destination, service)
            if tag == 1:
                flash('Failed: adding route policies are reached limit or overlaps!!! Please try to use ten digit times(10-99).')
                exit_login(self)
                return count
        # add tens digit
        for i in range(0, int(times) // 10 % 10):
            count, tag = tendigit_add_route_policy(self, count,  routename, interface, metric, source, destination, service)
            if tag == 1:
                flash('Failed: adding route policies are reached limit!!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count
        # add the single digit
        count = unidigit_add_route_policy(self, count,  routename, interface, metric, source, destination, service, times)
        current_app.logger.warning(
            '[' + current_user.fullname + ']--end of add, total add route policies---------------%s' % count)
    else:
        flash('input error...')

    exit_login(self)
    return count

def add_route_policies(dutip, dutuser, dutpwd, routename, interface, metric, source, destination, service, times):
    current_app.logger.warning('[' + current_user.fullname + ']--start add Route Policies ...')
    if routename == 'auto':
        routename = random_word()
        current_app.logger.warning('[' + current_user.fullname + ']--Determine that localname is auto and start generating random names...')
        cont = dynamic_route_policy(dutip, dutuser, dutpwd, routename, interface, metric, source, destination, service, times)
    else:
        cont = dynamic_route_policy(dutip, dutuser, dutpwd, routename, interface, metric, source, destination, service, times)
    return cont

def add_nat_cmd(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable):

    self.sendline('nat-policy inbound %s outbound %s source host %s translated-source host %s destination host %s translated-destination host %s service group %s translated-service group %s' % (inbound, outbound, source[count], translatedsource[count], destination[count], translateddestination[count], service, translatedservice))
    #self.expect(loginprompt)
    print(self.before.decode())
    self.sendline('yes')
    self.sendline('yes')
    self.sendline('yes')
    self.sendline('yes')
    self.expect('#')
    self.sendline('name auto_%s_%s' % (natname, count))
    self.expect('#')
    self.sendline('%s' % natenable)
    self.expect('#')
    self.sendline('exit')
    self.expect('#')
    current_app.logger.warning(
        '[' + current_user.fullname + ']--start add the nat policy -----------> auto_%s_%s !' % (natname, count))
    return self

def add_nat_commit(self, count, natname):
    self.sendline('commit')
    self.expect('#')
    strs = self.before.decode()
    end_2_line = strs.split('\r\n')[-2]
    #print(strs)
    #print(end_2_line.find('Maximum Policies'))
    #print(end_2_line.find('overlaps'))
    #print(end_2_line.find('Too many Network objects'))
    #if len(re.findall('Maximum Policies', line_2)) or len(re.findall('overlaps', line_2)) == 0:
    if end_2_line.find('Maximum Policies') == -1 and end_2_line.find('overlaps') == -1 and end_2_line.find('Too many Network objects') == -1 and end_2_line.find('no matching command') == -1:
        tag = 0
        current_app.logger.warning(
            '[' + current_user.fullname + ']--add nat Policy: auto_%s_%s seccessful !' % (natname, count))
    else:
        tag = 1
        flash(end_2_line)
        current_app.logger.warning('[' + current_user.fullname + ']--' + end_2_line)
    return self, tag

def unidigit_add_nat_policy(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable, times):
    for count in range(count, int(times)):
        count += 1
        self = add_nat_cmd(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable)
        self, tag = add_nat_commit(self, count, natname)
        if tag == 1:
            self.sendline('no address-group ipv4 %s' % source[count])
            self.sendline('no address-group ipv4 %s' % destination[count])
            self.sendline('no address-group ipv4 %s' % translatedsource[count])
            self.sendline('no address-group ipv4 %s' % translateddestination[count])
            #self.expect('#')
            return count
    return count

def tendigit_add_nat_policy(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable):
    tmp_ao = {}
    tmp_ao2 = {}
    tmp_ao3 = {}
    tmp_ao4 = {}
    for m in range(0, 10):
        count += 1
        self = add_nat_cmd(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable)
        tmp_ao[m+1] = source[count]
        tmp_ao2[m + 1] = destination[count]
        tmp_ao3[m + 1] = translatedsource[count]
        tmp_ao4[m + 1] = translateddestination[count]
    self, tag = add_nat_commit(self, count, natname)
    if tag == 1:
        for i in range(1, 11):
            self.sendline('no address-group ipv4 %s' % tmp_ao[i])
            self.sendline('no address-group ipv4 %s' % tmp_ao2[i])
            self.sendline('no address-group ipv4 %s' % tmp_ao3[i])
            self.sendline('no address-group ipv4 %s' % tmp_ao4[i])
    return count, tag

def centile_add_nat_policy(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable):
    tmp_ao = {}
    tmp_ao2 = {}
    tmp_ao3 = {}
    tmp_ao4 = {}
    for j in range(0, 100):
        count += 1
        self = add_nat_cmd(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable)
        tmp_ao[j+1] = source[count]
        tmp_ao2[j + 1] = destination[count]
        tmp_ao3[j + 1] = translatedsource[count]
        tmp_ao4[j + 1] = translateddestination[count]

    self, tag = add_nat_commit(self, count, natname)
    if tag == 1:
        for i in range(1, 101):
            self.sendline('no address-group ipv4 %s' % tmp_ao[i])
            self.sendline('no address-group ipv4 %s' % tmp_ao2[i])
            self.sendline('no address-group ipv4 %s' % tmp_ao3[i])
            self.sendline('no address-group ipv4 %s' % tmp_ao4[i])
    return count, tag

def dynamic_nat_policy(dutip, dutuser, dutpwd, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable, times):
    count = 0
    self = ssh_login(dutip, dutuser, dutpwd)
    source = increased_ipv4(source, times)
    translatedsource = increased_ipv4(translatedsource, times)
    destination = increased_ipv4(destination, times)
    translateddestination = increased_ipv4(translateddestination, times)

    if int(times) < 101:
        #add centile digit
        for n in range(0, int(times) // 10):
            count, tag = tendigit_add_nat_policy(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable)
            if tag == 1:
                flash('Failed: nat policies are reached limit or overlaps !!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count
        #add the single digit
        count = unidigit_add_nat_policy(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable, times)
        current_app.logger.warning('[' + current_user.fullname + ']--end of add, total add nat policies---------------%s' % count)

    elif int(times) > 101 and int(times) < 1000:
        # add tens digit
        for n in range(0, int(times) // 100):
            count, tag = centile_add_nat_policy(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable)
            if tag == 1:
                flash('Failed: adding nat policies are reached limit or overlaps!!! Please try to use ten digit times(10-99).')
                exit_login(self)
                return count
        # add tens digit
        for i in range(0, int(times) // 10 % 10):
            count, tag = tendigit_add_nat_policy(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable)
            if tag == 1:
                flash('Failed: adding nat policies are reached limit!!! Please try to use single digit times(1-9).')
                exit_login(self)
                return count
        # add the single digit
        count = unidigit_add_nat_policy(self, count, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable, times)
        current_app.logger.warning(
            '[' + current_user.fullname + ']--end of add, total add nat policies---------------%s' % count)
    else:
        flash('input error...')

    exit_login(self)
    return count

def add_nat_policies(dutip, dutuser, dutpwd, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable, times):
    current_app.logger.warning('[' + current_user.fullname + ']--start add nat Policies ...')
    if natname == 'auto':
        natname = random_word()
        current_app.logger.warning('[' + current_user.fullname + ']--Determine that localname is auto and start generating random names...')
        cont = dynamic_nat_policy(dutip, dutuser, dutpwd, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable, times)
    else:
        cont = dynamic_nat_policy(dutip, dutuser, dutpwd, natname, inbound, outbound, source, translatedsource, destination, translateddestination, service, translatedservice, natenable, times)
    return cont


