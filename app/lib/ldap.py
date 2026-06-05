# -*- coding: utf-8 -*-

from ldap3 import Server, Connection, ALL, SUBTREE, ServerPool, MODIFY_REPLACE, extend, SAFE_SYNC
from ..lib.mongodb import mongo

qaldapinfo = mongo().find_one('GlobalConfig', 'id', 'NewQALDAP')
shldapinfo = mongo().find_one('GlobalConfig', 'id', 'NewSHLDAP')

SH_LDAP_SERVER_POOL = shldapinfo['SH_LDAP_SERVER_POOL']
SH_LDAP_SERVER_PORT = shldapinfo['SH_LDAP_SERVER_PORT']
SH_ADMIN_DN = shldapinfo['SH_ADMIN_DN']
SH_ADMIN_PASSWORD = shldapinfo['SH_ADMIN_PASSWORD']
SH_SEARCH_BASE = shldapinfo['SH_SEARCH_BASE']

QA_LDAP_SERVER_POOL = qaldapinfo['QA_LDAP_SERVER_POOL']
QA_LDAP_SERVER_PORT = qaldapinfo['QA_LDAP_SERVER_PORT']
QA_ADMIN_DN = qaldapinfo['QA_ADMIN_DN']
QA_ADMIN_PASSWORD = qaldapinfo['QA_ADMIN_PASSWORD']
QA_SEARCH_BASE = qaldapinfo['QA_SEARCH_BASE']


def sh_ldap_auth(username, password):
    ldap_server_pool = ServerPool(SH_LDAP_SERVER_POOL)
    conn = Connection(ldap_server_pool, user=SH_ADMIN_DN, password=SH_ADMIN_PASSWORD)
    print('sh ldap conn.result: %s' % conn.result)
    print('sh ldap conn.check_names: %s' % conn.check_names)
    tsr = conn.open()
    print('tsr: %s' % tsr)
    conn.bind()

    res = conn.search(
        search_base=SH_SEARCH_BASE,
        search_filter='(sAMAccountName={})'.format(username),
        search_scope=SUBTREE,
        attributes=['cn', 'givenName', 'mail', 'sAMAccountName'],
        paged_size=5
    )
    print('sh ldap res： %s' % res)
    if res:
        entry = conn.response[0]
        dn = entry['dn']
        attr_dict = entry['attributes']

        # check password by dn
        try:
            conn2 = Connection(ldap_server_pool, user=dn, password=password)
            print('sh ldap conn2.result: %s' % conn2.result)
            print('sh ldap conn2.check_names: %s' % conn2.check_names)
            conn2.bind()
            if conn2.result["description"] == "success":
                # print((True, attr_dict["mail"], attr_dict["sAMAccountName"], attr_dict["givenName"]))
                return (True, attr_dict["mail"], attr_dict["sAMAccountName"], attr_dict["givenName"])
            else:
                print("auth fail")
                return (False, None, None, None)
        except Exception as e:

            return (False, None, None, None)
    else:
        return (False, None, None, None)


def qa_ldap_auth(username, password):
    ldap_server_pool = ServerPool(QA_LDAP_SERVER_POOL)
    conn = Connection(ldap_server_pool, user=QA_ADMIN_DN, password=QA_ADMIN_PASSWORD)
    print('qa ldap conn.result: %s' % conn.result)
    print('qa ldap conn.result: %s' % conn.check_names)
    conn.open()
    conn.bind()
    # print(conn.result)
    # print(conn.check_names)
    res = conn.search(
        search_base=QA_SEARCH_BASE,
        search_filter='(sAMAccountName={})'.format(username),
        search_scope=SUBTREE,
        attributes=['cn', 'givenName', 'mail', 'sAMAccountName'],
        paged_size=5
    )
    # print(res)
    if res:
        entry = conn.response[0]
        dn = entry['dn']
        attr_dict = entry['attributes']

        # check password by dn
        try:
            conn2 = Connection(ldap_server_pool, user=dn, password=password)
            conn2.bind()
            if conn2.result["description"] == "success":
                # print((True, attr_dict["mail"], attr_dict["sAMAccountName"], attr_dict["givenName"]))
                return (True, attr_dict["mail"], attr_dict["sAMAccountName"], attr_dict["givenName"])
            else:
                print("auth fail")
                return (False, None, None, None)
        except Exception as e:

            return (False, None, None, None)
    else:
        return (False, None, None, None)


# def qa_ldap_modify(new_pwd):
#     # ldap_server_pool = ServerPool(QA_LDAP_SERVER_POOL)
#     # conn = Connection(ldap_server_pool, user=QA_ADMIN_DN, password=QA_ADMIN_PASSWORD)
#     # print('qa ldap conn.result: %s' % conn.response)
#     # print('qa ldap conn.result: %s' % conn.check_names)
#     conn = Connection(
#         server=Server(
#             '10.103.2.37',
#             # use_ssl=False,
#             connect_timeout=2,
#             port=389
#         ),
#         user='administrator@vlab',
#         password='sonicpassword',
#         client_strategy=SAFE_SYNC
#     )
#     # conn.open()
#     # conn.bind()
#     user = "CN=lezhang,OU=qa,DC=vlab,DC=com"
#     username= 'lezhang'
#
#     new_pwd = 'sonicauto'
#
#     conn.bind()
#     res = conn.search(
#         search_base=QA_SEARCH_BASE,
#         search_filter='(sAMAccountName={})'.format(username),
#         search_scope=SUBTREE,
#         attributes=['cn', 'givenName', 'mail', 'sAMAccountName'],
#         paged_size=5
#     )
#     print(f'search result: {res[0]}')
#     res = extend.microsoft.modifyPassword.ad_modify_password(conn, user, new_pwd, 'password',  controls=None)
#     print(res)
#     status = conn.modify(
#         dn=user,
#         changes={
#             'userPassword': [(MODIFY_REPLACE, [new_pwd])],
#             'unicodePwd': [(MODIFY_REPLACE, [f'"{new_pwd}"'.encode('utf-16-le')])],
#             'userAccountControl': [(MODIFY_REPLACE, [66080])]
#         }
#     )
#     print(status)
#     conn.unbind()



# if __name__ == "__main__":
#     qa_ldap_modify('sonicwall')

#    ldap_auth("lezhang", "********")
