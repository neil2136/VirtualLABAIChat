#!/usr/bin/env python
from pyVim.connect import SmartConnect, Disconnect, SmartConnectNoSSL
from pyVmomi import vim
from ..mongodb import mongo
import atexit

MAX_DEPTH = 10
def LoginExsi(esxiip, AdminUser, AdminPass):
    try:
        si = SmartConnectNoSSL(host=esxiip, user=AdminUser, pwd=AdminPass, port=443)
        atexit.register(Disconnect, si)
    except vim.fault.InvalidLogin:
        raise SystemExit('Unable to connect to host, with supplied credentials.')
    content = si.RetrieveContent()
    return content

def GetPoolAndVmname(content):
    # path: content.rootFolder.childEntity[0].hostFolder.childEntity[0].resourcePool.resourcePool
    vmlist = {}
    for root in content.rootFolder.childEntity:
        if hasattr(root, 'vmFolder'):
            for hostFolder in root.hostFolder.childEntity:
                if hasattr(hostFolder, 'resourcePool'):
                    for layer2folder in hostFolder.resourcePool.resourcePool:
                        # print(layer2folder.name)
                        for layer2vm in layer2folder.vm:
                            vmlist[printvminfo(layer2vm)] = layer2folder.name
                        if hasattr(layer2folder, 'resourcePool'):
                            for layer3folder in layer2folder.resourcePool:
                                for layer3vm in layer3folder.vm:
                                    vmlist[printvminfo(layer3vm)] = layer2folder.name
    # print(vmlist)
    return vmlist

def MakeVMInfo(vm, vmlist, esxiip):
            vminfo = GetAllNics(vm)
            vminfo['esxihost'] = esxiip
            vminfo['vmname'] = vm.summary.config.name
            vminfo['uuid'] = vm.summary.config.uuid

def printvminfo(vm, depth=0):
    """
    Print information for a particular virtual machine or recurse into a folder
    with depth protection
    """
    # if this is a group it will have children. if it does, recurse into them
    # and then return
    if hasattr(vm, 'childEntity'):
        if depth > MAX_DEPTH:
            return
        for child in vm.childEntity:
            printvminfo(child, depth+1)
        return
    summary = vm.summary
    return summary.config.name

def GetAllNics(vm):
    avm = {}
    anic = []
    for dev in vm.config.hardware.device:
        #get the disk size
        if isinstance(dev, vim.vm.device.VirtualDisk):
            if isinstance(dev.deviceInfo, vim.Description):
                disksize = dev.deviceInfo.summary
                # print('dev deviceInfo summary:   %s' % disksize)
                avm['disksize'] = disksize
        #get the nic information
        # print(dev)
        if isinstance(dev, vim.vm.device.VirtualVmxnet) or isinstance(dev, vim.vm.device.VirtualE1000e) or isinstance(dev, vim.vm.device.VirtualE1000) or isinstance(dev, vim.vm.device.VirtualPCNet32):
            adapter = dev.deviceInfo.label
            mac = dev.macAddress
            portgroup = dev.backing.deviceName
            nicpower = 'On' if dev.connectable.startConnected is True else 'Off'
            vlanid = portgroup.split('vlan')[-1]
            anic.append({'adapter': adapter,
                         'mac': mac, 'portgroup': portgroup, 'vlan': vlanid,
                         'nicpower': nicpower})
    avm['nicsinfo'] = anic
    return avm

def SyncAVM(esxiip, AdminUser, AdminPass, vmname, svname):
    content = LoginExsi(esxiip, AdminUser, AdminPass)
    vms = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    for vm in vms.view:
        # print(vm.name)
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
            vminfo = GetAllNics(vm)
            vminfo['esxihost'] = esxiip
            vminfo['vmname'] = vm.summary.config.name
            vminfo['uuid'] = vm.summary.config.uuid
            vminfo['memorysize'] = vm.summary.config.memorySizeMB
            vminfo['numethernetcards'] = vm.summary.config.numEthernetCards
            vminfo['numcpu'] = vm.summary.config.numCpu
            vminfo['vmpower'] = vm.runtime.powerState
            vminfo['owner'] = svname
            vminfo['user'] = svname
            #print('vminfo :    %s' % vminfo)
            return vminfo
    vms.Destroy()
    return None

def SyncMyVM(esxiip, AdminUser, AdminPass, svname):
    content = LoginExsi(esxiip, AdminUser, AdminPass)
    vmlist = GetPoolAndVmname(content)
    vms = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vmsinfo = []
    for vm in vms.view:
        vmname = vm.summary.config.name
        if vmname in vmlist.keys():
            if vmlist[vmname] == svname:
                vminfo = GetAllNics(vm)
                vminfo['esxihost'] = esxiip
                vminfo['vmname'] = vm.summary.config.name
                vminfo['uuid'] = vm.summary.config.uuid
                vminfo['memorysize'] = vm.summary.config.memorySizeMB
                vminfo['numethernetcards'] = vm.summary.config.numEthernetCards
                vminfo['numcpu'] = vm.summary.config.numCpu
                vminfo['vmpower'] = vm.runtime.powerState
                vminfo['owner'] = svname
                vminfo['user'] = svname
                vmsinfo.append(vminfo)
                # vminfo.clear()
    # print('vmsinfo :    %s' % vmsinfo)
    return vmsinfo

def SyncAllVM(esxip, esxuser, esxpassword):
    db = mongo()
    content = LoginExsi(esxip, esxuser, esxpassword)
    vmlist = GetPoolAndVmname(content)
    vms = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vmsinfo = []
    for vm in vms.view:
        vmname = vm.summary.config.name
        if vmname in vmlist.keys():
            vminfo = GetAllNics(vm)
            vminfo['esxihost'] = esxip
            vminfo['vmname'] = vmname
            vminfo['uuid'] = vm.summary.config.uuid
            vminfo['memorysize'] = vm.summary.config.memorySizeMB
            vminfo['numethernetcards'] = vm.summary.config.numEthernetCards
            vminfo['numcpu'] = vm.summary.config.numCpu
            vminfo['vmpower'] = vm.runtime.powerState
            vminfo['owner'] = vmlist[vmname]
            vminfo['user'] = vmlist[vmname]
            vmsinfo.append(vminfo)
            # vminfo.clear()
    # print('vmsinfo :    %s' % vmsinfo)
    if vmsinfo:
        db.delete_many('VM', 'esxihost', esxip)
        for vm in vmsinfo:
            db.insert_one('VM', vm)
    print('Sync info: check Esxi %s finished, update count: %s' % (esxip, len(vmsinfo)))
