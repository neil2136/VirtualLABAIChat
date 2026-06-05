import atexit
import sys
import time
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim

def ChangeVMName(host, user, pwd, vmname, newname):
    si = None
    try:
        si = SmartConnectNoSSL(host=host, user=user, pwd=pwd, port=443)
        atexit.register(Disconnect, si)
    except vim.fault.InvalidLogin:
        raise SystemExit('Unable to connect to host, with supplied credentials.')
    content = si.RetrieveContent()
    datacenters = content.rootFolder.childEntity
    # vmFolders = content.rootFolder.childEntity[0].vmFolder.childEntity
    try:
        obj = None
        while datacenters:
            entity = datacenters.pop()
            if entity.name == vmname:
                obj = entity
                break
            elif isinstance(entity, vim.Datacenter):
                # add this vim.DataCenter's folders to our search
                # we don't know the entity's type so we have to scan
                # each potential folder...
                datacenters.append(entity.datastoreFolder)
                datacenters.append(entity.hostFolder)
                datacenters.append(entity.networkFolder)
                datacenters.append(entity.vmFolder)
            elif isinstance(entity, vim.Folder):
                # add all child entities from this folder to our search
                datacenters.extend(entity.childEntity)

        if obj is None:
            print('A object named %s could not be found' % vmname)
            exit()
            return 'fail'

        # if newname:
        #     new_name = newname
        # else:
        #     # just because we want the script to do *something*
        #     new_name = vmname + "0"
        # print('name        : %s' % obj.name)
        # print('    renaming from %s to %s' % (vmname, new_name))
        # rename creates a task...
        print("rename VM {}".format(vmname))
        task = obj.Rename(newname)
        while task.info.state not in [vim.TaskInfo.State.success,
                                      vim.TaskInfo.State.error]:
            time.sleep(1)
        print('rename result: '+task.info.state)
        return task.info.state
    except RuntimeError:
        raise SystemExit('Unable to set VLAN, with supplied credentials.')


