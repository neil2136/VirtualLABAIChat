import atexit
import sys
import time
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim

def VMPowerCtrl(host, user, pwd, vmname, operate):
    si = None
    try:
        si = SmartConnectNoSSL(host=host, user=user, pwd=pwd, port=443)
        atexit.register(Disconnect, si)
    except vim.fault.InvalidLogin:
        raise SystemExit('Unable to connect to host, with supplied credentials.')
    content = si.RetrieveContent()
    # datacenters = content.rootFolder.childEntity
    # vmFolders = content.rootFolder.childEntity[0].vmFolder.childEntity
    # 判断虚拟机是否存在
    try:
        # vm = service_instance.content.rootFolder.find_by_name(vm_name)
        vm = None
        entity_stack = content.rootFolder.childEntity
        while entity_stack:
            entity = entity_stack.pop()
            if entity.name == vmname:
                vm = entity
                del entity_stack[0:len(entity_stack)]
            elif hasattr(entity, 'childEntity'):
                entity_stack.extend(entity.childEntity)
            elif isinstance(entity, vim.Datacenter):
                entity_stack.append(entity.vmFolder)

    except Exception as e:
        print('could not find the childEntity with Datacenter')
        return 'fail'

    if not isinstance(vm, vim.VirtualMachine):
        print('could not find a virtual machine with VirtualMachine !')
        return 'fail'
    if operate == 'poweredOff':
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            print("powering off VM {}".format(vmname))
            task = vm.PowerOff()
            while task.info.state not in [vim.TaskInfo.State.success,
                                          vim.TaskInfo.State.error]:
                time.sleep(1)
            print("power is off. "+task.info.state)
            return task.info.state
    elif operate == 'poweredOn':
        if vm.runtime.powerState != vim.VirtualMachinePowerState.poweredOn:
            print("powering on VM {}".format(vmname))
            task = vm.PowerOn()
            while task.info.state not in [vim.TaskInfo.State.success,
                                          vim.TaskInfo.State.error]:
                time.sleep(1)
            print("power is on. "+task.info.state)
            return task.info.state
    elif operate == 'reboot':
            task = vm.ResetVM_Task()
            while task.info.state not in [vim.TaskInfo.State.success,
                                          vim.TaskInfo.State.error]:
                time.sleep(1)
            print("power is reboot. "+task.info.state)
            return task.info.state

