#!/usr/bin/env python
import re
import time
from datetime import datetime
from ..lib.utm.utm import Firewall
from .mongodb import mongo


def LongTasksLog(type, device, operated, snname):
    db = mongo()
    dtime = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
    deshdata = {'svname': snname, 'type': type, 'device': device,
                'operated': operated, 'time': dtime}
    db.insert_one('longtasklog', deshdata)


def CheckStatus(output):
    # print('1111111111111111111111')
    # print(output)
    # print('2222222222222222222222')
    print('uptime-------------------------------------------')
    print('start check fw status...')
    fwstatus = {}
    print('show status system')
    # Up Time:                       0 Days 23:29:28
    findtime = re.findall('(?<=Up Time: {23}).+', output)
    if findtime:
        # fwuptime = findtime[0] if findtime else None
        # fwstatus['uptime'] = fwuptime.strip()
        fwuptime = re.findall('\d+ \S+ \d+:\d+:\d+', findtime[0])
        if fwuptime:
            fwstatus['uptime'] = fwuptime[0]
    else:
        print('can not find the up time in status')
        fwstatus['uptime'] = ''
    print(f'fwstatus add uptime: {fwstatus}')

    print('version------------------------------------------')
    print('diag show build-info')
    # Firmware Version: SonicOS 7.1.0-6068-P3405
    findversion = re.findall('(?<=Firmware Version: SonicOS).+', output)
    if findversion:
        # version = findversion[0].split(' ')[-1]
        # fwstatus['version'] = version.strip()
        version = re.findall('\d+.\d+.\d+-\d+-\S\d+', findversion[0])
        if version:
            fwstatus['version'] = version[0]

    else:
        print('can not find the fw version in diag')
        fwstatus['version'] = ''
    print(f'fwstatus version: {fwstatus}')

    print('interfaces--------------------------------------------')
    print('show status interfaces')
    fwips = []
    # MGMT(MGMT)       10.8.124.37   1 Gbps Full Duplex
    findips = re.findall('MGMT\S+ +\d+.\d+.\d+.\d+.+', output)
    if findips:
        interip = re.findall('\d+.\d+.\d+.\d+', findips[0])[0]
        # linkfilter = re.findall('\d+.\d+.\d+.\d+ .+', findips[0])[0]
        # interlink = re.split('\d+.\d+.\d+.\d+ ', linkfilter)[-1]
        interlink = ''
        if 'No link' in findips[0]:
            interlink = 'No link'
        else:
            linkcheck = re.findall('\d \S+ \S+ \S+', findips[0])
            if linkcheck:
                interlink = linkcheck[0]
        fwips.append({'port': 'MGMT', 'ip': interip, 'linkstatus': interlink})
    print('fwips------------------------------------------------')

    # X0(LAN)         192.168.168.168  1 Gbps Full Duplex
    findips = re.findall('X\S+ +\d+.\d+.\d+.\d+.+', output)
    if findips:
        for inter in findips:
            print(f'inter: {inter}')
            interport = re.findall('X\d+', inter)[0]
            interip = re.findall('\d+.\d+.\d+.\d+', inter)[0]
            # linkfilter = re.findall('\d+.\d+.\d+.\d+ .+', inter)[0]
            # interlink = re.split('\d+.\d+.\d+.\d+ ', linkfilter)[-1].strip()
            interlink = ''
            if 'No link' in findips[0]:
                interlink = 'No link'
            else:
                linkcheck = re.findall('\d \S+ \S+ \S+', findips[0])
                if linkcheck:
                    interlink = linkcheck[0]
            fwips.append({'port': interport, 'ip': interip, 'linkstatus': interlink})
    print(f'fwips add Xi: {fwips}')
    print('check status end------------------------------------------------')
    return fwstatus, fwips


def GetCoreDumpList(output):
    print('start get fw coredump list...')
    try:
        dumplist = re.findall('\S+.core.zst.gpg', output)
        if not dumplist:
            dumplist = re.findall('\S+.core.zst', output)
        print(f'dumplist result: {dumplist}')
        # ['U2022-02-13_22-42-08_start-sonicos.s_202_tz570p_7.0.1-5048-P2332.core.zst.gpg ']
        realdump = []
        if dumplist:
            for dump in dumplist:
                dumptime = re.findall('\d+-\d+-\d+_\d+-\d+-\d+', dump)
                # ['2022-02-13_22-42-08']
                shiptime = dumptime[0].split('_')
                dumptime = shiptime[0] + ' ' + shiptime[1].replace('-', ':')
                coretime = datetime.strptime(dumptime, "%Y-%m-%d %H:%M:%S")
                # datetime.datetime(2022, 2, 13, 22, 42, 8)
                nowtime = datetime.now()
                # datetime.datetime(2022, 11, 18, 14, 21, 3, 39505)
                if (nowtime - coretime).days < 7:
                    print(f'nowtime: {nowtime} - coretime: {coretime} < 7 days')
                    realdump.append(dump)
                else:
                    print(f'nowtime: {nowtime} - coretime: {coretime} > 7 days')
            realdump = rmredundancy(realdump)
            # print(f'realdump: {realdump}')
            return realdump
        else:
            print('can not find the 7 days coredump in fw.')
            return []
    except BaseException as e:
        print(e)
        print('get coredump list from fw failed.')
        return []


def rmredundancy(output):
    if '\\' in output:
        output = output.split('\\')[0]
    if '[' in output:
        output = output.split('[')[0]
    return output


def fwcheck(output):
    print('CheckStatus-----------------------------------------------------')
    (fwstatus, fwips) = CheckStatus(output)

    print('GetCoreDumpList-----------------------------------------------------')
    fwcoredump = GetCoreDumpList(output)
    fwstatus['coredump'] = fwcoredump
    print(f'fwstatus add coredump: {fwstatus}')
    dates = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(time.time()))
    fwstatus['errormsg'] = ''
    fwstatus['updatelog'] = f'{dates}: Auto update FW Status successful !'
    print('fwcheck end-----------------------------------------------------')
    return fwstatus, fwips, ''


def getfwinfo(console_ip, console_port, soniccore, adutinfo):
    cmds = ['show status system', 'show status interfaces', 'diag show build-info',
            'export core-dump ' + chr(9)]
    fw_console = Firewall('fw_ip',
                          soniccore=soniccore,
                          console_ip=console_ip,
                          console_port=console_port,
                          user='admin',
                          password=g_savedfwpwd,
                          blade=1,
                          supported_config_mode='cli-console')
    (res, output) = fw_console.do_cli_commands(cmds, tag=1)
    if res:
        if '15700' in adutinfo['Product'] or '14700' in adutinfo['Product']:
            cmd = ['export core-dump ' + chr(9)]
            for i in range(2, 5):
                nssp_console = Firewall('fw_ip',
                                        soniccore=adutinfo['Soniccore'][0],
                                        console_ip=console_ip,
                                        console_port=console_port,
                                        user='admin',
                                        password=g_savedfwpwd,
                                        blade=i,
                                        supported_config_mode='cli-console')
                (res, msg) = nssp_console.do_cli_commands(cmd, tag=1)
                output += msg
    # print(f'111111111111111111111111111111\n{output}\n22222222222222222222222222222222222222')
    return res, output


def synccoredumps(console_ip, console_port, soniccore, getdutinfo):
    if 'FWStatus' in getdutinfo.keys() and 'coredump' in getdutinfo['FWStatus'].keys() and getdutinfo['FWStatus']['coredump']:
    # if getdutinfo['FWStatus']['coredump']:
        # check HA status:  not Secondary STANDBY
        # check file server via ping in fw
        cmds = ['show high-availability status', 'ping 10.103.2.127']
        fw_console = Firewall('fw_ip',
                              soniccore=soniccore,
                              console_ip=console_ip,
                              console_port=console_port,
                              user='admin',
                              password=g_savedfwpwd,
                              blade=1,
                              supported_config_mode='cli-console')
        (res, output) = fw_console.do_cli_commands(cmds, tag=1)
        if 'Secondary STANDBY' in output:
            msg = 'fw is in HA and Status is Secondary STANDBY, can not export core dump.'
            return False, msg
        if 'is alive' not in output:
            msg = 'fw can not connect file server 10.103.2.127, export core dump failed.'
            return False, msg
        try:
            for dump in getdutinfo['FWStatus']['coredump']:
                cmds = [f'export core-dump {dump} scp root@10.103.2.127:/var/www/html/bigfile/coredumps',
                        'yes', 'password']
                fw_console = Firewall('fw_ip',
                                      soniccore=soniccore,
                                      console_ip=console_ip,
                                      console_port=console_port,
                                      user='admin',
                                      password=g_savedfwpwd,
                                      blade=1,
                                      supported_config_mode='cli-console')
                return fw_console.do_cli_commands(cmds, tag=1)
        except Exception as e:
            print(repr(e))
            msg = 'export core-dump cmd process failed via console, please manual check.'
            return False, msg
    else:
        print('not coredump need to export.')
        return True, 'not coredump need to export.'


def checkdutinfo(console_ip, console_port, adutinfo, svname, taskcount):
    print('checkdutinfo====================================================================================')
    print('start get dut information...')
    global g_savedfwpwd

    db = mongo()
    if 'savedfwpwd' in adutinfo.keys():
        g_savedfwpwd = adutinfo['savedfwpwd']
    else:
        print('can not get saved fw password in db...')
        g_savedfwpwd = 'password'
    if 'Soniccore' in adutinfo.keys():
        soniccore = adutinfo['Soniccore'][0]
    else:
        soniccore = {'user': '', 'password': ''}
    res, output = getfwinfo(console_ip, console_port, soniccore, adutinfo)
    if res:
        (fwstatus, fwips, errormsg) = fwcheck(output)
        if errormsg:
            LongTasksLog(adutinfo['DeviceType'], adutinfo['Product'], f'TASK{taskcount}: {errormsg}', svname)
            print('get firewall status failed, telnet console manager or login FW failed.')
        else:
            db.update_one('DUT', 'id', adutinfo['id'], 'FWStatus', fwstatus)
            db.update_one('DUT', 'id', adutinfo['id'], 'ProductType', 'G7')
            for fwip in fwips:
                for interinfo in adutinfo['InterfaceInfo']['Interface']:
                    if fwip['port'] == interinfo['name']:
                        db.update_one_inerface('DUT', adutinfo['id'], interinfo['name'], 'fwip', fwip['ip'])
                        db.update_one_inerface('DUT', adutinfo['id'], interinfo['name'], 'linkstatus',
                                               fwip['linkstatus'])
            msg = f'get firewall ({adutinfo["id"]}) {adutinfo["Product"]} all status successed'
            LongTasksLog(adutinfo['DeviceType'], adutinfo['Product'], f'TASK{taskcount}: {msg}', svname)
            print(msg)
    else:
        print('send cmd to dut failed.')
        dates = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(time.time()))
        fwstatus = {'errormsg': output,
                    'updatelog': f'{dates}: {output}'}
        db.update_one('DUT', 'id', adutinfo['id'], 'FWStatus', fwstatus)
        LongTasksLog(adutinfo['DeviceType'], adutinfo['Product'], f'TASK{taskcount}: {output}', svname)
        print('get firewall status failed, telnet console manager or login FW failed.')
    print('checkdutinfo====================================================================================')
    print('synccoredumps====================================================================================')
    print('start sync core dumps.')
    getdutinfo = db.find_one('DUT', 'id', adutinfo['id'])
    res, msg = synccoredumps(console_ip, console_port, soniccore, getdutinfo)
    if not res:
        dates = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(time.time()))
        getdutinfo['FWStatus']['updatelog'] = f'{dates}: {msg}'
        db.update_one('DUT', 'id', getdutinfo['id'], 'FWStatus', getdutinfo['FWStatus'])
    print('sync core dump finished.')
    print('synccoredumps====================================================================================')

    return fwcheck(output)
