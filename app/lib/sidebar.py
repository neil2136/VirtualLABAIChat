import json
import os
import time
from flask_login import current_user
from .mongodb import mongo
from ..models import *
from .topbar import SearchDeviceVLAN
from ..lib.cductrl import CDU
from ..main.tasks import async_checkdutinfo
from ..lib.flashandlog import long_tasks_log
from ..lib.refreshg7 import checkdutinfo


def GetFilePath():
    listdir = 'users/' + current_user.svname
    pathfwlist = listdir + '/fwlist.txt'
    pathsplist = listdir + '/splist.txt'
    pathlentlist = listdir + '/lentlist.txt'
    pathvmlist = listdir + '/vmlist.txt'
    pathvlanlist = listdir + '/vlanlist.txt'
    return pathfwlist, pathsplist, pathlentlist, pathvmlist, pathvlanlist


def GetSidebarList():
    db = mongo()
    pathfwlist, pathsplist, pathlentlist, pathvmlist, pathvlanlist = GetFilePath()
    if current_user.svname not in os.listdir('users') \
            or os.path.isfile(pathfwlist) == False \
            or os.path.isfile(pathsplist) == False \
            or os.path.isfile(pathlentlist) == False \
            or os.path.isfile(pathvmlist) == False \
            or os.path.isfile(pathvlanlist) == False:
        RefreshAllSidebar(pathfwlist, pathsplist, pathlentlist, pathvmlist, pathvlanlist)
    fwlists = open(pathfwlist, 'r')
    splists = open(pathsplist, 'r')
    lentlists = open(pathlentlist, 'r')
    vmlists = open(pathvmlist, 'r')
    vlanlists = open(pathvlanlist, 'r')
    fwfilters = json.load(fwlists)
    spfilters = json.load(splists)
    lentfwfilters = json.load(lentlists)
    vmfilters = json.load(vmlists)
    vlanfilters = json.load(vlanlists)
    fwlists.close()
    splists.close()
    lentlists.close()
    vmlists.close()
    vlanlists.close()
    publicpool = db.find_many_sort('DUT', 'Owner', 'Public', 'id', 'up')
    return fwfilters, spfilters, lentfwfilters, vmfilters, vlanfilters, publicpool


def RefreshAllSidebar(pathfwlist, pathsplist, pathlentlist, pathvmlist, pathvlanlist):
    if current_user.svname not in os.listdir('users'):
        os.mkdir('users/' + current_user.svname)
    if os.path.isfile(pathfwlist) == False:
        os.mknod(pathfwlist)
    if os.path.isfile(pathsplist) == False:
        os.mknod(pathsplist)
    if os.path.isfile(pathlentlist) == False:
        os.mknod(pathlentlist)
    if os.path.isfile(pathvmlist) == False:
        os.mknod(pathvmlist)
    if os.path.isfile(pathvlanlist) == False:
        os.mknod(pathvlanlist)

    fwlists, splists, lentlists = GetDUTList()
    vmlists = GetVMList()
    vlanlists = GetVLANList()

    with open(pathfwlist, 'w+') as f:
        f.writelines(json.dumps(fwlists))
    with open(pathsplist, 'w+') as f:
        f.writelines(json.dumps(splists))
    with open(pathlentlist, 'w+') as f:
        f.writelines(json.dumps(lentlists))
    with open(pathvmlist, 'w+') as f:
        f.writelines(json.dumps(vmlists))
    with open(pathvlanlist, 'w+') as f:
        f.writelines(json.dumps(vlanlists))


def GetDUTList():
    db = mongo()
    lentlist = []
    user = db.find_one('User', 'svname', current_user.svname)
    fwfilters = db.find_many_sort('DUT', 'User', user['svname'], 'id', 'up')

    spfilters = db.find_many_sort('SonicPoint', 'User', user['svname'], 'id', 'up')
    lentfwfilters = db.find_many_sort('DUT', 'Owner', user['fullname'], 'id', 'up')
    for lentfwfilter in lentfwfilters:
        if not lentfwfilter['User'] == user['svname']:
            # print(lentfwfilter['User'])
            lentlist.append(lentfwfilter)
    lentspfilters = db.find_many_sort('SonicPoint', 'Owner', user['fullname'], 'id', 'up')
    for lentspfilter in lentspfilters:
        if not lentspfilter['User'] == user['svname']:
            # print(lentspfilter['User'])
            lentlist.append(lentspfilter)
    # print(lentlist)
    # print(fwfilters)
    return fwfilters, spfilters, lentlist


def GetVMList():
    db = mongo()
    vmlists = []
    esxiplist = db.find_one('User', 'svname', current_user.svname)
    for esxip in esxiplist['ESXServer']:
        vmnamelist = []
        esxifind = db.find_by_multi_field('VM', 'owner', current_user.svname, 'esxihost', esxip)
        for vminfo in esxifind:
            vmnamelist.append(vminfo['vmname'])
        # 创建无重复元素列表并排序
        vmlist = sorted(list(set(vmnamelist)))
        vmlists.append({'ip': esxip, 'name': vmlist})
    return vmlists


def GetVLANList():
    db = mongo()
    userinfo = db.find_one('User', 'svname', current_user.svname)
    vlanlists = []
    functionvlan = db.find_one('GlobalConfig', 'id', 'FunctionVLAN')
    privatevlan = []
    for vlan in userinfo['VLAN']:
        result = SearchDeviceVLAN(vlan)
        if result:
            privatevlan.append({'vlan': vlan, 'inused': 'inused'})
        else:
            privatevlan.append({'vlan': vlan, 'inused': ''})
    adminvlan = []
    for vlan in userinfo['AdminVLAN']:
        result = SearchDeviceVLAN(vlan)
        if result:
            adminvlan.append({'vlan': vlan, 'inused': 'inused'})
        else:
            adminvlan.append({'vlan': vlan, 'inused': ''})
    ixiavlan = []
    for vlan in functionvlan['ixia']:
        result = SearchDeviceVLAN(vlan)
        if result:
            inused = ''
            for dut in result:
                if dut['User'] == current_user.svname:
                    inused = 'inused'
            ixiavlan.append({'vlan': vlan, 'inused': inused})
        else:
            ixiavlan.append({'vlan': vlan, 'inused': ''})
    tousvlan = []
    for vlan in functionvlan['tous']:
        result = SearchDeviceVLAN(vlan)
        if result:
            inused = ''
            for dut in result:
                if dut['User'] == current_user.svname:
                    inused = 'inused'
            tousvlan.append({'vlan': vlan, 'inused': inused})
        else:
            tousvlan.append({'vlan': vlan, 'inused': ''})

    vlanlists.append({'type': 'admin', 'id': adminvlan})
    vlanlists.append({'type': 'private', 'id': privatevlan})
    vlanlists.append({'type': 'ixia', 'id': ixiavlan})
    vlanlists.append({'type': 'tous', 'id': tousvlan})
    # print(vlanlists)
    return vlanlists


def RefreshDUT():
    pathfwlist, pathsplist, pathlentlist, pathvmlist, pathvlanlist = GetFilePath()
    fwlists, splists, lentlists = GetDUTList()
    with open(pathfwlist, 'w+') as f:
        f.writelines(json.dumps(fwlists))
    with open(pathsplist, 'w+') as f:
        f.writelines(json.dumps(splists))
    with open(pathlentlist, 'w+') as f:
        f.writelines(json.dumps(lentlists))


def RefreshVM():
    pathvmlist = GetFilePath()[-2]
    vmlists = GetVMList()
    with open(pathvmlist, 'w+') as f:
        f.writelines(json.dumps(vmlists))


def RefreshVLAN():
    pathvlanlist = GetFilePath()[-1]
    vlanlists = GetVLANList()
    with open(pathvlanlist, 'w+') as f:
        f.writelines(json.dumps(vlanlists))


def GetVMsName():
    db = mongo()
    vmlists = []
    esxiplist = db.find_one('User', 'svname', current_user.svname)
    # print(esxiplist)
    for esxip in esxiplist['ESXServer']:
        # print(esxip)
        vmlist = []
        vmnames = []
        esxifind = db.find_by_multi_field(VL.EsxiVMs, EsxiVMs.esxihost, esxip, EsxiVMs.owner, current_user.svname)
        # print(esxifind)
        for esxiline in esxifind:
            if esxiline['vmname'] not in vmnames:
                # print(esxiline)
                vmlist.append(esxiline['vmname'])
        # vmlist = {'esxip': esxip, 'vmnames': vmnames}
        vmlist.append(esxip)
        vmlist = list(set(vmlist))
        vmlists.append(sorted(vmlist))
    # print(sorted(vmlists))
    return sorted(vmlists)


# GetVMsNames('10.8.2.107', 'ldu')

def RefreshG7(option):
    db = mongo()
    cdu = CDU()
    product = []
    allg7dut = []
    taskcount = 1
    # notallowcheck = ['307', '308', '312', '311']
    if option == 'mydevice':
        allg7dut = db.find_many('DUT', 'id', '953')
        # allg7dut = db.find_by_multi_field('DUT', 'User', current_user.svname, 'ProductType', 'G7')
    elif option == 'all':
        # allg7dut = db.find_many('DUT', 'id', '83')
        allg7dut = db.find_many('DUT', 'ProductType', 'G7')
        # allg7dut = db.find_by_multi_field('DUT', 'User', 'lbian', 'ProductType', 'G7')
        # allg7dut = db.find_many_sort('DUT', 'User', 'jnzhang', 'id', 'up')
        # allg7dut = db.find_many('DUT', 'id', '328')
        # allg7dut = db.find_by_multi_field('DUT', 'User', 'jnzhang', 'ProductType', 'G7')
        # allg7dut = db.find_many('DUT', 'ProductType', 'G7')
    if not allg7dut:
        return 'can not find g7 device in current user.'
    for adutinfo in allg7dut:
        powerstatus = []
        product.append(f'({adutinfo["id"]}) {adutinfo["Product"]}')

        print('start**********************************************************************')
        print(f'start check dut: {adutinfo["id"]}, {adutinfo["Product"]}')
        if 'Forbidden' in adutinfo['FWScripts']:
            msg = 'cancel check because of owner requirement.'
            dates = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(time.time()))
            fwstatus = {"errormsg": msg, "updatelog": f'{dates}: {msg}'}
            db.update_one('DUT', 'id', adutinfo['id'], 'FWStatus', fwstatus)
            print(msg)
        else:
            for powerinfo in adutinfo['PowerInfo']:
                power_name = powerinfo['PowerController']
                power_channel = powerinfo['PowerChannel']
                power_map = db.find_one('PowerController', 'id', power_name)
                powercheck = cdu.Check_CDU(power_map['IPAddress'], power_channel)
                powerstatus.append(True if powercheck == 'On' else False)
            print(f'dut power: {powerstatus}')
            if not all(powerstatus):
                dates = time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(time.time()))
                fwstatus = {'errormsg': 'dut power off',
                            'updatelog': f'{dates}: Auto update FW Status failed. DUT power off.'}
                db.update_one('DUT', 'id', adutinfo['id'], 'FWStatus', fwstatus)
                print('get firewall status failed,DUT power off.')
            else:
                consoleinfo = db.find_one('ConsoleManager', 'id', adutinfo['ConsoleInfo']['ConsoleManager'])
                if option == 'all':
                    task_process = async_checkdutinfo.apply_async((
                        consoleinfo['IPAddress'],
                        adutinfo['ConsoleInfo']['TelnetPort'],
                        adutinfo, 'all', taskcount))
                    time.sleep(2)
                    print(
                        f'run check dut {adutinfo["id"]}, {adutinfo["Product"]} info finished. result: {task_process}')
                else:
                    task_process = async_checkdutinfo.apply_async((
                        consoleinfo['IPAddress'],
                        adutinfo['ConsoleInfo']['TelnetPort'],
                        adutinfo, current_user.svname, taskcount))
                    print(f'run check dut info to long task finished. task_process: {task_process}')
                taskcount += 1
            print(f'sync dut: {adutinfo["id"]} status finished! ')
            print('end%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
    msg = f'Start sync all G7 dut status in queue,total {len(product)},include: {product}'
    if option == 'mydevice':
        long_tasks_log('Queue', 'ALL DUT', msg)
        print(msg)
    return 'ok'
