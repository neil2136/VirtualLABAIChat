#!/usr/bin/env python
import atexit, operator
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim
from ..mydevices import GetEsxiHost
from ..mongodb import mongo
from flask_login import current_user

MAX_DEPTH = 10

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
        vmlist = vm.childEntity
        for child in vmlist:
            printvminfo(child, depth+1)
        return

    summary = vm.summary
    return summary.config.name

def FindVMsName():
    # args = setup_args()
    global vm_dict
    si = None
    vmdicts = []
    esx = GetEsxiHost()
    db = mongo()
    if esx:
        # print('esx: %s' % esx)
        for esxnum in esx:
            vm_dict = []
            # print('IPAddress: %s, AdminUser: %s, AdminPass: %s' % (esxnum['IPAddress'], esxnum['AdminUser'], esxnum['AdminPass']))
            try:
                si = SmartConnectNoSSL(host=esxnum['IPAddress'], user=esxnum['AdminUser'], pwd=esxnum['AdminPass'], port=443)
                atexit.register(Disconnect, si)
            except vim.fault.InvalidLogin:
                raise SystemExit('Unable to connect to host, with supplied credentials.')
            content = si.RetrieveContent()
            # path: content.rootFolder.childEntity[0].hostFolder.childEntity[0].resourcePool.resourcePool
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
                                    if layer2folder.name == current_user.svname:
                                        # print(dir(layer2folder))
                                        if hasattr(layer2folder, 'resourcePool'):
                                            for layer3folder in layer2folder.resourcePool:
                                                # print(layer3folder.name)
                                                for layer3vm in layer3folder.vm:
                                                    vm_dict.append(printvminfo(layer3vm))
                                        for layer2vm in layer2folder.vm:
                                            vm_dict.append(printvminfo(layer2vm))
            #                         else:
            #                             print('not pool name: %s in ESXI host: %s' % (current_user.svname, esxnum['IPAddress']))
            #                 else:
            #                     print('Not found pool in root folder !')
            #                     return AttributeError
            #         else:
            #             print('Not found vmFolder in content.rootFolder.childEntity !')
            #             return AttributeError
            except RuntimeError:
                return SystemExit('find attribute from vmFolder or resourcePool in Exsi Error.')
            vm_dict.append(esxnum['IPAddress'])
            vmdicts.append(sorted(vm_dict))
        print('vmdicts---------%s' % vmdicts)
        return sorted(vmdicts)
        # return sorted(esxi_list, key=operator.itemgetter('esxiip'), reverse=False)
    else:
        return None

