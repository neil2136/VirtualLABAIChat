from pymongo import MongoClient
import pymongo, operator
import traceback, re
from .. lib.global_var import *
from config import MONGODB_CONFIG
# from .log import log_error

def MongoConn():
    # 连接mongodb
    client = pymongo.MongoClient(host=MONGODB_CONFIG['host'], port=MONGODB_CONFIG['port'])
    #client = pymongo.MongoClient(host='10.103.2.36', port=27017)
    # 指定数据库
    db = client.VL
    return db
def TransferSpecialStr(str):
    new_str = ""
    special = ['/', '^', '$', '*', '+', '?', '.', '(', ')']
    for c in str:
        if c in special:
            new_str += '\\'
        new_str += c
    return new_str

class mongo(object):

    def find_one(self, collections, name, value):
        try:
            db = MongoConn()
            find_rst = db[collections].find_one({name: value}, {'_id': 0})
            #print(find_rst)
            if collections == 'DUT' or collections == 'SonicPoint':
                if 'lastKeep' in find_rst:
                    del find_rst['lastKeep']
            # if find_rst == None:
            #     print('find_one: Cannot find the data in mongo db. collections:%s,name:%s,value:%s' % (collections, name, value))
            return find_rst
        except Exception:
            print(traceback.format_exc())
            return None
    def find_many(self, collections, name, value):
        result_find_many = []
        try:
            db = MongoConn()
            for x in db[collections].find({name: value}, {'_id': 0}):
                if 'lastKeep' in x:
                    del x['lastKeep']
                result_find_many.append(x)
            #print(result_find_many)
            # if result_find_many == []:
            #     print(
            #         'find_many: Cannot find the data in mongo db. collections:%s,name:%s,value:%s' % (collections, name, value))
            return result_find_many
        except Exception:
            print(traceback.format_exc())
            return None
    def find_many_sort(self, collections, name, value, sortname, sortorder):
        result_find_many = []
        try:
            db = MongoConn()
            if sortorder == 'up':
                order = pymongo.ASCENDING
            else:
                order = pymongo.DESCENDING
            for x in db[collections].find({name: value}, {'_id': 0}).sort(sortname, order):
                if 'lastKeep' in x:
                    del x['lastKeep']
                result_find_many.append(x)
            #print(result_find_many)
            # if result_find_many == []:
            #     print(
            #         'find_many: Cannot find the data in mongo db. collections:%s,name:%s,value:%s' % (collections, name, value))
            return result_find_many
        except Exception:
            print(traceback.format_exc())
            return None

    def find_by_regex(self, collections, name, value):
        result_find_regex = []
        try:
            db = MongoConn()
            #不区分大小写
            # newname = '^%s$' % value
            # print(newname)
            # re_name = re.compile(newname, re.IGNORECASE)
            # print(re_name)
            # for x in db[collections].find({name: re_name}, {'_id': 0}):
            #     if 'lastKeep' in x:
            #         del x['lastKeep']
            #     result_find_regex.append(x)
            for x in db[collections].find({name: {"$regex": TransferSpecialStr(value)}}, {'_id': 0}):
                if 'lastKeep' in x:
                    del x['lastKeep']
                result_find_regex.append(x)
            #print(result_find_regex)
            # if result_find_regex == []:
            #     print(
            #         'find_many: Cannot find the data in mongo db. collections:%s,name:%s,value:%s' % (
            #         collections, name, value))
            return result_find_regex
        except Exception:
            print(traceback.format_exc())
            return None

    def find_by_multi_field(self, collections, key1, value1, key2, value2):
        result_find = []
        try:
            db = MongoConn()
            # for x in db[collections].find({name: {"$regex": value}}, {'_id': 0}):
            #for x in db[collections].find({$and: [{ key1: value1},{ key2: value2 }]}):
            for x in db[collections].find({"$and": [{key1: {"$regex": TransferSpecialStr(value1)}}, {key2: {"$regex": TransferSpecialStr(value2)}}]}, {'_id': 0}):
                if 'lastKeep' in x:
                    del x['lastKeep']
                result_find.append(x)
            #print(result_find)
            # if result_find == []:
            #     print(
            #         'find_many: Cannot find the data in mongo db. collections:%s,name:%s,value:%s' % (
            #         collections, key1, value1))
            return result_find
        except Exception:
            print(traceback.format_exc())
            return None

    def find_all(self, collections, sort_id):
        try:
            get_result = []
            db = MongoConn()
            get_results = db[collections].find().sort(sort_id, pymongo.ASCENDING)
            # get_results = vl_conn.db[collections].find().sort('id', pymongo.ASCENDING)
            for result in get_results:
                if '_id' in result:
                    del result['_id']
                if 'lastKeep' in result:
                    del result['lastKeep']
                if 'Rack' in result:
                    del result['Rack']
                # else:
                # print('_id don not in key !')
                get_result.append(result)
            # if get_result == []:
            #     print(
            #         'find_all: Cannot find the data in mongo db. collections:%s,sort_id:%s' % (collections, sort_id))
            #get_result = sorted(get_result, key=operator.itemgetter(sort_id), reverse=False)
            # print(get_result)
            return get_result
        except Exception:
            print(traceback.format_exc())

    def find_all_lab_dut(self, collections, sort_id, sortorder='up'):
        try:
            get_result = []
            db = MongoConn()
            if sortorder == 'up':
                order = pymongo.ASCENDING
            else:
                order = pymongo.DESCENDING

            consoleinfo = self.find_all('ConsoleManager', 'id')
            powerinfo = self.find_all('PowerController', 'id')

            # get_results = db[collections].find().sort(sort_id, pymongo.ASCENDING)
            get_results = db[collections].find().sort(sort_id, order)
            for result in get_results:
                if '_id' in result:
                    del result['_id']
                if 'lastKeep' in result:
                    del result['lastKeep']
                if 'Rack' in result:
                    del result['Rack']
                if 'InterfaceInfo' in result:
                    del result['InterfaceInfo']
                for coninfo in consoleinfo:
                    if result['ConsoleInfo']['ConsoleManager'] == coninfo['id']:
                        result['ConsoleInfo']['ip'] = coninfo['IPAddress']
                for pinfo in powerinfo:
                    if result['PowerInfo'][0]['PowerController'] == pinfo['id']:
                        result['PowerInfo'][0]['ip'] = pinfo['IPAddress']
                result['id'] = int(result['id'])
                get_result.append(result)
                get_result = sorted(get_result, key=lambda keys: keys['id'])
            return get_result
        except Exception:
            print(traceback.format_exc())
            return []

    def find_all_sort(self, collections, sortname, sortorder):
        try:
            get_result = []
            db = MongoConn()
            if sortorder == 'up':
                order = pymongo.ASCENDING
            else:
                order = pymongo.DESCENDING
            get_results = db[collections].find().sort(sortname, order)
            # print(get_results)
            for result in get_results:
                if '_id' in result:
                    del result['_id']
                if 'lastKeep' in result:
                    del result['lastKeep']
                get_result.append(result)
            return get_result
        except Exception:
            print(traceback.format_exc())
            return None

    def update_one(self, collections, search_name, search_value, change_name, change_value):
        db = MongoConn()
        try:
            update = db[collections].update_one({search_name: search_value}, {'$set': {change_name: change_value}})
            # print(update)
            return update
        except Exception:
            print(traceback.format_exc())
            return None
    def update_one_inerface(self, collections, id, interface, change_name, change_value):
        db = MongoConn()
        try:
            update = db[collections].update_one({'id': id}, {'$set': {'InterfaceInfo.Interface.$[d].' + change_name: change_value}}, upsert=False, array_filters=[{'d.name': interface}])
            #print(update)
            return update
        except Exception:
            print(traceback.format_exc())
            return None
    def update_subkey(self, collections, search_key, search_value, subkey, search_subid, search_subname, change_name, change_value):
        db = MongoConn()
        try:
            update = db[collections].update_one({search_key: search_value}, {'$set': {subkey + '.$[d].' + change_name: change_value}}, upsert=False, array_filters=[{'d.' + search_subid: search_subname}])
            #print(update)
            return update
        except Exception:
            print(traceback.format_exc())
            return None
    def update_many(self, collections, search_name, search_value, change_name, change_value):
        db = MongoConn()
        try:
            update = db[collections].update_many({search_name: search_value}, {'$set': {change_name: change_value}})
            # print(update)
            return update
        except Exception:
            print(traceback.format_exc())
            return None
    def insert_one(self, collections, insert_document):
        db = MongoConn()
        try:
            insert = db[collections].insert_one(insert_document)
            #print(insert)
            return insert
        except Exception:
            print(traceback.format_exc())
            return None
    def insert_many(self, collections, insert_list):
        db = MongoConn()
        try:
            insert = db[collections].insert_many(insert_list)
            #print(insert)
            return insert
        except Exception:
            print(traceback.format_exc())
            return None
    def delete_one(self, collections, id, delete_document):
        db = MongoConn()
        try:
            delete = db[collections].delete_one({id: delete_document})
            #print(delete)
            return delete
        except Exception:
            print(traceback.format_exc())
            return None
    def delete_many(self, collections, id, delete_document):
        db = MongoConn()
        try:
            delete = db[collections].delete_many({id: delete_document})
            #print(delete)
            return delete
        except Exception:
            print(traceback.format_exc())
            return None
    def delete_many_multi(self, collections, key1, value1, key2, value2):
        db = MongoConn()
        try:
            delete = db[collections].delete_many({key1: value1, key2: value2})
            # print('333333333333333:    '+str(delete.deleted_count))
            #print(delete)
            return delete
        except Exception:
            print(traceback.format_exc())
            return None

    def delete_all(self, collections):
        db = MongoConn()
        try:
            delete = db[collections].delete_many({})
            print(collections+' documents delete counts: %s' % delete.deleted_count)
            return delete
        except Exception:
            print(traceback.format_exc())
            return None
