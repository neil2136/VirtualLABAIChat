from .mongodb import *
from flask_login import current_user
from .dbcollect import *
from .flashandlog import flash_and_log_info, flash_and_log_error, LogAndCounts
from .switchcfg import sw_port_refresh
from .esxi.change_vm_vlan import ChangeVMVlan

def RegetDUTInfo(type, id):
    db = mongo()
    adeviceget = db.find_one(type, 'id', id)
    consoleip = db.find_one('ConsoleManager', 'id', adeviceget['ConsoleInfo']['ConsoleManager'])
    adeviceget['ConsoleInfo']['ip'] = consoleip['IPAddress']
    for powerinfo in adeviceget['PowerInfo']:
        cduip = db.find_one('PowerController', 'id', powerinfo['PowerController'])
        powerinfo['ip'] = cduip['IPAddress']
    # print(adeviceget)
    dutvlanpool = MyDUTVLANRange()
    vmvlanpool = MyVMVLANRange()
    # vlan_ranges = CombineRanges(user_check['AdminVLAN'], user_check['VLAN'])
    # print(adeviceget)
    return adeviceget, dutvlanpool, vmvlanpool

def DUTPortRefresh(id, type, dutport, operate):
    db = mongo()
    adeviceget = db.find_one(type, 'id', id)
    # print(adeviceget)
    portline = adeviceget['InterfaceInfo']['Interface']
    for portname in portline:
        if portname['name'] == dutport:
            ptype = portname['porttype']
            swfind = db.find_one('Switch', 'id', portname['SwitchID'])
            swip = swfind['ConsoleServer']
            swchannel = portname['SwitchPort']
            # portsetresult, portpower, portmode, untagvlan, tagvlan, stp, lag, consoledata = sw_port_refresh(ptype, swip, swchannel, operate)
            refres = sw_port_refresh(ptype, swip, swchannel, operate)
            eventhead = 'Refresh Result(type %s, id %s, interface %s): ' % (type, id, dutport)
            if refres['msg'] == 'login fail':
                event = eventhead+'Login Switch Failed.Unable to establish physical connection ! '
                # flash_and_log_error(event)
                LogAndCounts(type, adeviceget['Product'], event, 0)
            elif refres['msg'] == 'lag on':
                db.update_one_inerface(type, id, dutport, 'portpower', refres['port_power'])
                db.update_one_inerface(type, id, dutport, 'lag', refres['lag'])
                event = eventhead+'Warning: LAG is ON, Only support read only in VLAB !'
                LogAndCounts(type, adeviceget['Product'], event, 0)
            elif refres['msg'] == 'vlan fail':
                db.update_one_inerface(type, id, dutport, 'portpower', refres['port_power'])
                event = eventhead+'VLAN Check Failed. CMD \'show interfaces \''+swchannel+' status\''
                LogAndCounts(type, adeviceget['Product'], event, 0)
            elif refres['msg'] == 'not switchport':
                db.update_one_inerface(type, id, dutport, 'portpower', refres['port_power'])
                event = eventhead+'pre-configured Failed. not switchport in Switch %s:%s !'
                LogAndCounts(type, adeviceget['Product'], event, 0)
            elif refres['port_mode'] == 'pullout':
                event = eventhead+'Warning: The cable is pulled out over the interface !'
                LogAndCounts(type, adeviceget['Product'], event, 0)
            else:
                if refres['untag_vlan'] == '1' or refres['untag_vlan'] == '0' or refres['untag_vlan'] == '--':
                    refres['untag_vlan'] = 'UnusedNetwork'
                db.update_one_inerface(type, id, dutport, 'portpower', refres['port_power'])
                db.update_one_inerface(type, id, dutport, 'portmode', refres['port_mode'])
                db.update_one_inerface(type, id, dutport, 'untagvlan', refres['untag_vlan'])
                db.update_one_inerface(type, id, dutport, 'tagvlan', refres['tag_vlan'])
                db.update_one_inerface(type, id, dutport, 'stp', refres['stp'])
                db.update_one_inerface(type, id, dutport, 'lag', refres['lag'])
                if operate == 'refreshall':
                    # TBD Function
                    pass
                else:
                    LogAndCounts(type, adeviceget['Product'], eventhead + ' Refreshed Successful ! ', 1)
            return refres['consoledata']

def UpdateDBInterfaces(id, type, dutport, portmode, untagvlan, tagvlan, stp, portpower):
    db = mongo()
    db.update_one_inerface(type, id, dutport, 'portpower', portpower)
    db.update_one_inerface(type, id, dutport, 'portmode', portmode)
    db.update_one_inerface(type, id, dutport, 'untagvlan', untagvlan)
    db.update_one_inerface(type, id, dutport, 'tagvlan', tagvlan)
    db.update_one_inerface(type, id, dutport, 'stp', stp)

'''
def DUTPortPowerSet(id, type, dutport, operate):
    db = mongo()
    adeviceget = db.find_one(type, 'id', id)
    # print(adeviceget)
    portline = adeviceget['InterfaceInfo']['Interface']
    for portname in portline:
        if portname['name'] == dutport:
            ptype = portname['porttype']
            swfind = db.find_one('Switch', 'id', portname['SwitchID'])
            swip = swfind['ConsoleServer']
            swchannel = portname['SwitchPort']
            portsetresult, consoledata = sw_port_power_set(ptype, swip, swchannel, operate)

            return portsetresult, consoledata
'''

def DeviceVLANCheckInDB(type, id, portname):
    db = mongo()
    adeviceget = db.find_one(type, 'id', id)
    interfacelist = adeviceget['InterfaceInfo']['Interface']
    for interface in interfacelist:
        devicesports = []
        if interface['portmode'] == 'trunk':
            fwsearch = db.find_by_multi_field('DUT', 'User', current_user.svname,
                                              'InterfaceInfo.Interface.' + 'portmode',
                                              'trunk')
            spsearch = db.find_by_multi_field('SonicPoint', 'User', current_user.svname,
                                              'InterfaceInfo.Interface.' + 'portmode', 'trunk')
            searchlist = fwsearch + spsearch
            if searchlist:
                for searchone in searchlist:
                    portlist = searchone['InterfaceInfo']['Interface']
                    for portinfo in portlist:
                        if portinfo['portmode'] == 'trunk':
                            devicesports.append(
                                {'id': searchone['id'], 'name': searchone['Product'], 'devicetype': searchone['DeviceType'], 'port': portinfo['name'], 'power': portinfo['portpower']})
            if devicesports:
                db.update_one_inerface(type, id, interface['name'], 'tagdevice', devicesports)
            else:
                db.update_one_inerface(type, id, interface['name'], 'tagdevice', [])
        elif interface['portmode'] == 'access' and interface['name'] == portname:
            fwsearch = db.find_many('DUT', 'InterfaceInfo.Interface.' + 'untagvlan', interface['untagvlan'])
            spsearch = db.find_many('SonicPoint', 'InterfaceInfo.Interface.' + 'untagvlan', interface['untagvlan'])
            searchlist = fwsearch + spsearch
            if searchlist:
                for searchone in searchlist:
                    portlist = searchone['InterfaceInfo']['Interface']
                    for portinfo in portlist:
                        if portinfo['portmode'] == 'access' and portinfo['untagvlan'] == interface['untagvlan'] and searchone['id'] != id:
                            devicesports.append(
                                {'id': searchone['id'], 'name': searchone['Product'], 'devicetype': searchone['DeviceType'], 'port': portinfo['name'], 'power': portinfo['portpower']})
            if devicesports:
                db.update_one_inerface(type, id, interface['name'], 'untagdevice', devicesports)
            else:
                db.update_one_inerface(type, id, interface['name'], 'untagdevice', [])

def VMsVLANCheckInDB(type, id):
    db = mongo()
    adeviceget = db.find_one(type, 'id', id)
    interfacelist = adeviceget['InterfaceInfo']['Interface']
    for interface in interfacelist:
        vms = []
        if interface['portmode'] == 'trunk':
            trunklist = db.find_by_multi_field('VM', 'owner', current_user.svname, 'nicsinfo.vlan', 'trunk_4095')
            for esxvlan in trunklist:
                if esxvlan['nicsinfo']:
                    for nics in esxvlan['nicsinfo']:
                        if nics['vlan'] == 'trunk_4095':
                            vms.append({'name': esxvlan['vmname'], 'nic': (': NIC ' + nics['adapter'].split(' ')[-1]),
                                        'power': esxvlan['vmpower']})
        elif interface['untagvlan'] == '0' or interface['untagvlan'] == '1' or interface['untagvlan'] == '--' or interface['untagvlan'] == 'UnusedNetwork':
            vms = []
        else:
            accesslist = db.find_by_multi_field('VM', 'owner', current_user.svname, 'nicsinfo.vlan', interface['untagvlan'])
            for esxvlan in accesslist:
                if esxvlan['nicsinfo']:
                    for nics in esxvlan['nicsinfo']:
                        if nics['vlan'] == interface['untagvlan']:
                            vms.append({'name': esxvlan['vmname'], 'nic': (': NIC ' + nics['adapter'].split(' ')[-1]), 'power': esxvlan['vmpower']})
        if vms:
            db.update_one_inerface(type, id, interface['name'], 'vmname', vms)
        else:
            db.update_one_inerface(type, id, interface['name'], 'vmname',
                                   [{'name': 'Not', 'nic': ' VMs', 'power': 'poweredOff'}])
    # vms = [{'nic': '3', 'name': 'lezhang_ubuntu16'}, {'nic': '1', 'name': 'lezhang_ngp_35'}]

def VMVLANSet(vmname, adapter, mac, vlan):
    db = mongo()
    if vlan == 'UnusedNetwork':
        portgroup = 'UnusedNetwork'
    elif vlan == 'trunk':
        portgroup = 'trunk_4095'
    else:
        portgroup = current_user.svname + '_vlan' + vlan
    getuserinfo = db.find_one('User', 'svname', current_user.svname)
    for esxiip in getuserinfo['ESXServer']:
        esx = db.find_one('ESX', 'IPAddress', esxiip)
        changevlan = ChangeVMVlan(esx['IPAddress'], esx['AdminUser'], esx['AdminPass'], vmname, adapter, portgroup)
        if changevlan:
            db.update_one('EsxiVMs', 'mac', mac, 'vlan', vlan)
            db.update_one('EsxiVMs', 'mac', mac, 'portgroup', portgroup)
            LogAndCounts('VM', vmname, 'Change the host: %s, vmname: %s, adapter: %s to vlan: %s Successfully !' % (
            esx['IPAddress'], vmname, adapter, portgroup), 1)
        else:
            LogAndCounts('VM', vmname, 'Change the host: %s, vmname: %s, adapter: %s to vlan: %s failed !' % (
                esx['IPAddress'], vmname, adapter, portgroup), 0)

def GetEsxiHost():
    db =mongo()
    vmlist = []
    getuserinfo = db.find_one('User', 'svname', current_user.svname)
    for esxiip in getuserinfo['ESXServer']:
        esx = db.find_one('ESX', 'IPAddress', esxiip)
        vmlist.append(esx)
    # print(vmlist)
    return vmlist

def MyDUTVLANRange():
    db = mongo()
    user_check = db.find_one('User', 'id', current_user.svname)
    funcvlan = db.find_one('GlobalConfig', 'id', 'FunctionVLAN')
    vlanranges = user_check['AdminVLAN'] + user_check['VLAN'] + funcvlan['ixia'] + funcvlan['tous']
    vlanranges.append('UnusedNetwork')
    return vlanranges

def MyVMVLANRange():
    db = mongo()
    user_check = db.find_one('User', 'id', current_user.svname)
    funcvlan = db.find_one('GlobalConfig', 'id', 'FunctionVLAN')
    vlanranges = user_check['AdminVLAN'] + user_check['VLAN'] + funcvlan['ixia'] + funcvlan['tous']
    vlanranges.append('trunk_4095')
    vlanranges.append('UnusedNetwork')
    return vlanranges
