#!/usr/bin/env python
from pyVim.connect import SmartConnect, Disconnect, SmartConnectNoSSL
from pyVmomi import vim
from ..mydevices import GetEsxiHost
import atexit
from flask_login import current_user

MAX_DEPTH = 10
def LoginExsi(esxiip, AdminUser, AdminPass):
    try:
        si = SmartConnectNoSSL(host=esxiip, user=AdminUser, pwd=AdminPass, port=443)
        atexit.register(Disconnect, si)
    except vim.fault.InvalidLogin:
        raise SystemExit('Unable to connect to host, with supplied credentials.')
    content = si.RetrieveContent()
    return content

def GetVMHosts(content):
    print("Getting all ESX hosts ...")
    host_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
    obj = [host for host in host_view.view]
    host_view.Destroy()
    return obj

def GetVMs(content):
    print("Getting all VMs ...")
    vm_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    obj = [vm for vm in vm_view.view]
    vm_view.Destroy()
    return obj

def GetHostsPortgroups(hosts):
    print("Collecting portgroups on all hosts. This may take a while ...")
    hostPgDict = {}
    for host in hosts:
        print('host:      %s' % host)
        pgs = host.config.network.portgroup
        hostPgDict[host] = pgs
        print("\tHost {} done.".format(host.name))
    print("\tPortgroup collection complete.")
    return hostPgDict


def PrintVmInfo(vm):
    vmPowerState = vm.runtime.powerState
    print("Found VM:", vm.name + "(" + vmPowerState + ")")
    return GetVMNics(vm)

def GetVMNics(vm):
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualEthernetCard):
            dev_backing = dev.backing
            # print(dev_backing.network)
            portGroup = None
            vlanId = None
            vSwitch = None
            if hasattr(dev_backing.network, 'name'):
                portGroup = dev.backing.network.name
                vmHost = vm.runtime.host
                # print('vmhost----%s' % vmHost)
                # global variable hosts is a list, not a dict
                host_pos = hosts.index(vmHost)
                viewHost = hosts[host_pos]
                # print('viewHost----%s' % viewHost)
                # global variable hostPgDict stores portgroups per host
                pgs = hostPgDict[viewHost]
                for p in pgs:
                    if portGroup in p.key:
                        # print('port-------%s' % (p.port))
                        # print('vswitch-------%s' % (p.vswitch))
                        vlanId = str(p.spec.vlanId)
                        vSwitch = str(p.spec.vswitchName)
                        # print('pname: %s,vlanId: %s, vswitchName: %s' % (p.spec.name, p.spec.vlanId, p.spec.vswitchName))
            else:
                print('AttributeError: NoneType. object dev.backing.network.name has no attribute: name .')
            # if hasattr(dev_backing, 'port'):
            #     portGroupKey = dev.backing.port.portgroupKey
            #     dvsUuid = dev.backing.port.switchUuid
            #     try:
            #         dvs = content.dvSwitchManager.QueryDvsByUuid(dvsUuid)
            #     except:
            #         portGroup = "** Error: DVS not found **"
            #         vlanId = "NA"
            #         vSwitch = "NA"
            #     else:
            #         pgObj = dvs.LookupDvPortGroup(portGroupKey)
            #
            #         portGroup = pgObj.config.name
            #         vlanId = str(pgObj.config.defaultPortConfig.vlan.vlanId)
            #         vSwitch = str(dvs.name)
            # else:
            #     if hasattr(dev_backing.network, 'name'):
            #         portGroup = dev.backing.network.name
            #         vmHost = vm.runtime.host
            #         # print('vmhost----%s' % vmHost)
            #         # global variable hosts is a list, not a dict
            #         host_pos = hosts.index(vmHost)
            #         viewHost = hosts[host_pos]
            #         # print('viewHost----%s' % viewHost)
            #         # global variable hostPgDict stores portgroups per host
            #         pgs = hostPgDict[viewHost]
            #         for p in pgs:
            #             if portGroup in p.key:
            #                 # print('port-------%s' % (p.port))
            #                 # print('vswitch-------%s' % (p.vswitch))
            #                 vlanId = str(p.spec.vlanId)
            #                 vSwitch = str(p.spec.vswitchName)
            #                 # print('pname: %s,vlanId: %s, vswitchName: %s' % (p.spec.name, p.spec.vlanId, p.spec.vswitchName))
            #     else:
            #         print('AttributeError: NoneType. object dev.backing.network.name has no attribute: name .')
            if portGroup is None:
                portGroup = 'NA'
            if vlanId is None:
                vlanId = 'NA'
            if vSwitch is None:
                vSwitch = 'NA'
            # print('\t' + dev.deviceInfo.label + '->' + dev.macAddress +
            #       ' @ ' + vSwitch + '->' + portGroup +
            #       ' (VLAN ' + vlanId + ')')
            if vlanId == '0':
                vlanId = 'UnusedNetwork'
            nicpower = 'On' if dev.connectable.startConnected is True else 'Off'
            vmnicinfo = {'vmname': vm.name, 'vmpower': vm.runtime.powerState, 'adapter': dev.deviceInfo.label, 'mac': dev.macAddress, 'vswitch': vSwitch, 'portgroup': portGroup, 'vlan': vlanId, 'nicpower': nicpower}
            print(vmnicinfo)
            vms_nic_info.append(vmnicinfo)

def getvminfo(vm, depth=0):
    """
    Print information for a particular virtual machine or recurse into a folder
    with depth protection
    """
    # if this is a group it will have children. if it does, recurse into them
    # and then return
    if hasattr(vm, 'childEntity'):
        if depth > MAX_DEPTH:
            return
        vmlist = vm.childEntity
        for alist in vmlist:
            getvminfo(alist, depth+1)
        return
    summary = vm.summary
    return summary.config.name

def GetVMlist(content, currentname):
    vm_dict = []
    try:
        for child in content.rootFolder.childEntity:
            if hasattr(child, 'vmFolder'):
                hostFolder = child.hostFolder
                # print('vmfolder    %s' % dir(hostFolder))
                for hostFolder in hostFolder.childEntity:
                    # print(dir(resourcePool.resourcePool.resourcePool))
                    if hasattr(hostFolder, 'resourcePool'):
                        rootfolders = hostFolder.resourcePool.resourcePool
                        # print(dir(rootfolders))
                        for layer2folder in rootfolders:
                            # print(pool.name)
                            if layer2folder.name == currentname:
                                # print(dir(layer2folder))
                                if hasattr(layer2folder, 'resourcePool'):
                                    for layer3folder in layer2folder.resourcePool:
                                        # print(layer3folder.name)
                                        for layer3vm in layer3folder.vm:
                                            vm_dict.append(getvminfo(layer3vm))
                                for layer2vm in layer2folder.vm:
                                    vm_dict.append(getvminfo(layer2vm))
    except RuntimeError:
        return SystemExit('find attribute from vmFolder or resourcePool in Exsi Error.')
    return vm_dict

def GetVICInfo(esxiip, AdminUser, AdminPass, currentname):
    global content, hosts, hostPgDict, vms_nic_info, vmnames
    vms_nic_info = []
    try:
        si = SmartConnectNoSSL(host=esxiip, user=AdminUser, pwd=AdminPass, port=443)
        atexit.register(Disconnect, si)
    except vim.fault.InvalidLogin:
        raise SystemExit('Unable to connect to host, with supplied credentials.')
    content = si.RetrieveContent()
    hosts = GetVMHosts(content)
    print('hosts: %s' % hosts)
    vmnames = GetVMlist(content, currentname)
    print('vmnames: %s' % vmnames)
    hostPgDict = GetHostsPortgroups(hosts)
    vms = GetVMs(content)
    # print('vms: %s' % vms)
    for vm in vms:
        # if vm.name == 'kvm-ubt16':
        #     vms_nic_info = PrintVmInfo(vm)
        for namelist in vmnames:
            # print('namelist:     %s' % namelist)
            if vm.name == namelist:
                PrintVmInfo(vm)
        # for esxilist in esxiinfos:
        #     for namelist in esxilist:
        #         # print('namelist:     %s' % namelist)
        #         if vm.name == namelist:
        #             PrintVmInfo(vm)
    return vms_nic_info

def GetNics(vm, vmhosts, hostPgList, esxiip, svname):
    nicinfo = []
    avm = {}
    anic = []
    for dev in vm.config.hardware.device:
        #get the disk size
        if isinstance(dev, vim.vm.device.VirtualDisk):
            if isinstance(dev.deviceInfo, vim.Description):
                disksize = dev.deviceInfo.summary
                print('dev deviceInfo summary:   %s' % disksize)
                avm['disksize'] = disksize
        if isinstance(dev, vim.vm.device.VirtualEthernetCard):
            #change the nic power value to On Off
            nicpower = 'On' if dev.connectable.startConnected is True else 'Off'
            # print('changed nicpower------%s' % nicpower)
            portGroup = None
            vlanId = None
            vSwitch = None
            if hasattr(dev.backing.network, 'name'):
                portGroup = dev.backing.network.name
                vmHost = vm.runtime.host
                # global variable hosts is a list, not a dict
                host_pos = vmhosts.index(vmHost)
                viewHost = vmhosts[host_pos]
                # global variable hostPgDict stores portgroups per host
                pgs = hostPgList[viewHost]
                for p in pgs:
                    if portGroup in p.key:
                        vlanId = str(p.spec.vlanId)
                        vSwitch = str(p.spec.vswitchName)
                        # print('pname: %s,vlanId: %s, vswitchName: %s' % (p.spec.name, p.spec.vlanId, p.spec.vswitchName))
            else:
                print('AttributeError: NoneType. object dev.backing.network.name has no attribute: name .')
            if portGroup is None:
                portGroup = 'NA'
            if vlanId is None:
                vlanId = 'NA'
            if vSwitch is None:
                vSwitch = 'NA'
            if vlanId == '0':
                vlanId = 'UnusedNetwork'
            vmnicinfo = {'vmname': vm.name, 'vmpower': vm.runtime.powerState, 'adapter': dev.deviceInfo.label, 'mac': dev.macAddress, 'vswitch': vSwitch, 'portgroup': portGroup, 'vlan': vlanId, 'owner': svname, 'user': svname, 'esxihost': esxiip, 'nicpower': nicpower}
            nicinfo.append(vmnicinfo)
            anic.append({'adapter': dev.deviceInfo.label,
                         'mac': dev.macAddress, 'vswitch': vSwitch, 'portgroup': portGroup, 'vlan': vlanId, 'nicpower': nicpower})
    avm['nicsinfo'] = anic
    # print(avm)
    return nicinfo

def SyncAVMNic(esxiip, AdminUser, AdminPass, vmname, svname):
    hostPgList = {}
    child = LoginExsi(esxiip, AdminUser, AdminPass)
    vmhosts = GetVMHosts(child)
    for host in vmhosts:
        pgs = host.config.network.portgroup
        hostPgList[host] = pgs
    vms = GetVMs(child)
    for vm in vms:
        if vm.name == vmname:
            # print('vm summary:  %s' % dir(vm.summary.config))
            # print('vm summary name:  %s' % vm.summary.config.name)
            # print('vm summary uuid:  %s' % vm.summary.config.uuid)
            # print('vm summary ftInfo:  %s' % vm.summary.config.ftInfo)
            # print('vm summary memorySizeMB:  %s' % vm.summary.config.memorySizeMB)
            # print('vm summary numCpu:  %s' % vm.summary.config.numCpu)
            # print('vm summary numEthernetCards:  %s' % vm.summary.config.numEthernetCards)
            # print('vm summary numVirtualDisks:  %s' % vm.summary.config.numVirtualDisks)
            #
            # print('vm runtime:  %s' % dir(vm.runtime))
            # print('vm runtime host:  %s' % vm.runtime.host)
            # print('vm runtime maxMemoryUsage:  %s' % vm.runtime.maxMemoryUsage)
            # print('vm runtime powerState:  %s' % vm.runtime.powerState)
            # print('vm :  %s' % vm.config.hardware.device)
            vms_nic_info = GetNics(vm, vmhosts, hostPgList, esxiip, svname)
            return vms_nic_info
    return None

# def GetAllNics(vm):
#     avm = {}
#     anic = []
#     for dev in vm.config.hardware.device:
#         #get the disk size
#         if isinstance(dev, vim.vm.device.VirtualDisk):
#             if isinstance(dev.deviceInfo, vim.Description):
#                 disksize = dev.deviceInfo.summary
#                 print('dev deviceInfo summary:   %s' % disksize)
#                 avm['disksize'] = disksize
#         #get the nic information
#         if isinstance(dev, vim.vm.device.VirtualVmxnet):
#             adapter = dev.deviceInfo.label
#             mac = dev.macAddress
#             portgroup = dev.backing.deviceName
#             nicpower = 'On' if dev.connectable.startConnected is True else 'Off'
#             vlanid = portgroup.split('vlan')[-1]
#             anic.append({'adapter': adapter,
#                          'mac': mac, 'portgroup': portgroup, 'vlan': vlanid,
#                          'nicpower': nicpower})
#     avm['nicsinfo'] = anic
#     return avm
#
# def SyncVMInfo(esxiip, AdminUser, AdminPass, vmname, svname):
#     child = LoginExsi(esxiip, AdminUser, AdminPass)
#     vms = GetVMs(child)
#     for vm in vms:
#         if vm.name == vmname:
#             # print('vm summary:  %s' % dir(vm.summary.config))
#             # print('vm summary name:  %s' % vm.summary.config.name)
#             # print('vm summary uuid:  %s' % vm.summary.config.uuid)
#             # print('vm summary ftInfo:  %s' % vm.summary.config.ftInfo)
#             # print('vm summary memorySizeMB:  %s' % vm.summary.config.memorySizeMB)
#             # print('vm summary numCpu:  %s' % vm.summary.config.numCpu)
#             # print('vm summary numEthernetCards:  %s' % vm.summary.config.numEthernetCards)
#             # print('vm summary numVirtualDisks:  %s' % vm.summary.config.numVirtualDisks)
#             #
#             # print('vm runtime:  %s' % dir(vm.runtime))
#             # print('vm runtime host:  %s' % vm.runtime.host)
#             # print('vm runtime maxMemoryUsage:  %s' % vm.runtime.maxMemoryUsage)
#             # print('vm runtime powerState:  %s' % vm.runtime.powerState)
#             # print('vm :  %s' % vm.config.hardware.device)
#             vminfo = GetAllNics(vm)
#             vminfo['esxihost'] = esxiip
#             vminfo['vmname'] = vm.summary.config.name
#             vminfo['uuid'] = vm.summary.config.uuid
#             vminfo['memorysize'] = vm.summary.config.memorySizeMB
#             vminfo['numethernetcards'] = vm.summary.config.numEthernetCards
#             vminfo['numcpu'] = vm.summary.config.numCpu
#             vminfo['vmpower'] = vm.runtime.powerState
#             vminfo['owner'] = svname
#             vminfo['user'] = svname
#             print('vminfo :    %s' % vminfo)
#             return vminfo
#     return None