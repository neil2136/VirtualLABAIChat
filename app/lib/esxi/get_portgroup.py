#!/usr/bin/env python
import atexit
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
from ..mongodb import mongo as db

def get_obj(content, vimtype, name):
    """
    get_obj(content, [vim.Datastore], "Datastore Name")
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            # print(Item: + c.name) # for debugging
            obj = c
            break
    if not obj:
        print('not name in portgroup')
        # raise RuntimeError("Managed Object " + name + " not found.")
    return obj

def GetPortGroups(host, prefixname, vlanstart, vlanend):
    portgroups = []
    esx = db().find_one('ESX', 'IPAddress', host)
    try:
        service_instance = connect.SmartConnectNoSSL(host=host, user=esx['AdminUser'], pwd=esx['AdminPass'], port=443)
        atexit.register(connect.Disconnect, service_instance)
        content = service_instance.RetrieveContent()
        for partvlan in range(int(vlanstart), int(vlanend)+1):
            pgfullname = prefixname + '_vlan' + str(partvlan)
            # print('pgfullname: %s' % pgfullname)
            # searching for port group
            pg = get_obj(content, [vim.Network], pgfullname)
            if hasattr(pg, 'name'):
                if pgfullname == pg.name:
                    portgroups.append({pgfullname: 'Existing'})
                else:
                    portgroups.append({pgfullname: 'Not Exist'})
            else:
                portgroups.append({pgfullname: 'Not Exist'})

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : {0}".format(error.msg))
        return None
    return portgroups
