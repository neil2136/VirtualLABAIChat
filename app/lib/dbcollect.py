from itertools import groupby

# 冒泡排序(从小到大)
#list = [4, 2, 1, 5, 6, 7, 8, 11, 12, 13, 19]
#AdminVLAN = ['104', '105', '106', '911', '912']
#vlan = ['737', '738', '739', '731', '732', '733', '734', '735', '736', '740', '913', '914', '915', '916', '917', '918']
def ConventInt(vlan):
    int_list = []
    for i in range(len(vlan)):
        int_list.append(int(vlan[i]))
    #print('=============%s' % int_list)
    return int_list
#ConventInt(AdminVLAN + vlan)
def BubbleSort(sort):
    lst = sort
    for i in range(len(lst)):
        j = i + 1
        for j in range(len(lst)):
            if int(lst[i]) < int(lst[j]):
                x = lst[i]
                lst[i] = lst[j]
                lst[j] = x
    #print("排序后列表：{}".format(lst))
    #print(sort)
    return sort
def CombineRanges(publicvlan, privatevlan):
    vlans = ConventInt(publicvlan+privatevlan)
    order = BubbleSort(vlans)
    range_list = []
    fun = lambda x: x[1] - x[0]
    for k, g in groupby(enumerate(order), fun):
        l1 = [j for i, j in g]  # 连续数字的列表
        if len(l1) > 1:
            scop = str(min(l1)) + '-' + str(max(l1))  # 将连续数字范围用"-"连接
        else:
            scop = l1[0]
        range_list.append(str(scop))
        # print("连续数字范围：{}".format(scop))
    rang_list = ','.join(range_list)
    print(rang_list)
    return rang_list
#CombineRanges(AdminVLAN, vlan)

def SplitRanges(vlans):
    if vlans == '--' or vlans == ' ' or vlans == '1':
        return ['--']
    vlanlist = []
    vlans_split = vlans.split(',')
    if len(vlans_split) > 1:
        for i in range(0, len(vlans_split)):
            #print(i)
            vlans_range = vlans_split[i].split('-')
            #print(vlans_range)
            for j in range(int(vlans_range[0]), int(vlans_range[-1])+1):
                vlanlist.append(str(j))
        #print(vlanlist)
    else:
        vlans_range = vlans.split('-')
        if len(vlans_range) > 1:
            for j in range(int(vlans_range[0]), int(vlans_range[-1])+1):
                vlanlist.append(str(j))
        else:
            vlanlist.append(vlans_range[0])
    #print(vlanlist)
    return vlanlist
#print(dell_sw_vlan_list('731-734,811-814'))