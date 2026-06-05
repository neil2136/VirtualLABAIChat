import atexit
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim
import time

def _get_obj(content, obj_type, name):
    # 根据对象类型和名称来获取具体对象
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, obj_type, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj

def LoginEsxi(host, user, pwd):
    try:
        si = SmartConnectNoSSL(host=host, user=user, pwd=pwd, port=443)
        atexit.register(Disconnect, si)
    except vim.fault.InvalidLogin:
        raise SystemExit('Unable to connect to host, with supplied credentials.')
    return si.RetrieveContent()

def ChangeVLANAndPower(host, user, pwd, vmname, adapter, vlan, nicstatus):
    content = LoginEsxi(host, user, pwd)
    datacenters = content.rootFolder.childEntity
    # vmFolders = content.rootFolder.childEntity[0].vmFolder.childEntity
    try:
        device_change = []
        for datacenter in datacenters:
            if hasattr(datacenter, 'vmFolder'):
                vmFolders = datacenter.vmFolder.childEntity
                for folder in vmFolders:
                    if folder.name == vmname:
                        devices = folder.config.hardware.device
                        # print(devices)
                        for device in devices:
                            # print(device.deviceInfo)
                            if device.deviceInfo.label == adapter:
                                # print(device.deviceInfo.label)
                                if isinstance(device, vim.vm.device.VirtualEthernetCard):
                                    nicspec = vim.vm.device.VirtualDeviceSpec()
                                    nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                                    nicspec.device = device
                                    nicspec.device.wakeOnLanEnabled = True
                                    nicspec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                                    nicspec.device.backing.network = _get_obj(content, [vim.Network], vlan)
                                    nicspec.device.backing.deviceName = vlan
                                    nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
                                    if nicstatus == 'On':
                                        nicspec.device.connectable.connected = True
                                        nicspec.device.connectable.startConnected = True
                                    elif nicstatus == 'Off':
                                        nicspec.device.connectable.connected = False
                                        nicspec.device.connectable.startConnected = False
                                    nicspec.device.connectable.allowGuestControl = True
                                    device_change.append(nicspec)
                        if device_change:
                            # print(device_change)
                            config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
                            task = folder.ReconfigVM_Task(config_spec)
                            while task.info.state not in [vim.TaskInfo.State.success,
                                                          vim.TaskInfo.State.error]:
                                time.sleep(1)
                            # print("Change VLAN status: " + task.info.state)
                            return task.info.state

                        else:
                            print('The network adapter does not exist and cannot modify the network !')
                            return 'fail'
    except RuntimeError:
        raise SystemExit('Unable to set VLAN, with supplied credentials.')
