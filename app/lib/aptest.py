import csv
import subprocess
import time

'''
需要传入参数:
result
groupid
'''


class ApTest:
    def __init__(self, groupid, host='qatest.eng.sonicwall.com', token='qatoken', user_name='qa_automation', retry=5, ):
        self.session_group_id = groupid
        self.host = host
        self.token = token
        self.user_name = user_name
        self.retry = retry
        self.uuid_map = {}

    def get_session_numbers_from_group_id(self, aptest_suite_name, session_group_id):
        rpc_query_string = '?suite=' + aptest_suite_name + '&sessiongroupid=' + session_group_id
        rpc_url = 'https://' + self.host + '/sw-getSessionsWithVar.pl' + rpc_query_string
        print("DEBUG: RPC URL is: " + rpc_url + '\n')
        params = ['--connect-timeout', '90', '--silent', '-k', rpc_url]

        print('mark--start  popen')
        rpc_result_string = subprocess.Popen(['curl'] + params, stdout=subprocess.PIPE).communicate()[0]
        print(rpc_result_string)
        return_string = rpc_result_string.decode('ASCII')
        rpc_result_list = return_string.split('\n')
        print(f"DEBUG: RPC result list:  {rpc_result_list} \n")
        rpc_return_value = rpc_result_list.pop(0)
        print("DEBUG: RPC result value is: " + rpc_return_value + '\n')
        for session_setname in rpc_result_list:
            print(session_setname)
            if session_setname == '':
                continue
            session_number, set_name = session_setname.split(',')
            rpc_query_string = '?suite=' + aptest_suite_name + '&set=' + set_name + '&session=' + session_number
            rpc_url = 'https://' + self.host + '/sw-autotclist.pl' + rpc_query_string
            print("DEBUG: RPC URL is: " + rpc_url + '\n')
            params = ['--connect-timeout', '20', '--silent', '-k']
            params.append(rpc_url)

            rpc_result_string = subprocess.Popen(['curl'] + params, stdout=subprocess.PIPE).communicate()[0]
            return_string = rpc_result_string.decode('ASCII')
            rpc_result_list_uuid = return_string.split('\n')
            print(rpc_result_list_uuid)
            rpc_return_code = rpc_result_list_uuid.pop(0)
            print("DEBUG: TC list result code is: " + rpc_return_code + '\n')
            if rpc_return_code == 1:
                print("Failed return status from getUUIDsFromSessionNumber" + '\n')
            elif len(rpc_result_list_uuid) == 1:
                print("No corresponding testcases for the given session number" + '\n')
            else:
                for testcase_data in rpc_result_list_uuid:
                    uuid = testcase_data.split(',')
                    self.uuid_map[uuid[0]] = session_number

    def update_results(self, aptest_suite_name, session_number, **row):
        print(row)
        uuid = row['uuid']
        result = ''
        _result = ''
        if 'result' in row:
            _result = row['result']
        note = ''
        # if 'note' in tc:
        # note = tc['note']
        custom_key = ''
        # if 'custom_key' in tc:
        # custom_key = tc['custom_key']
        custom_val = ''
        # if 'custom_val' in tc:
        # custom_val = tc['custom_val']
        note_default = ''
        transform_result = {'PASSED': 'pass', 'FAILED': 'fail', 'SKIPPED': 'untested'}
        if _result in transform_result:
            result = transform_result[_result]
        execdata = 'EXECDATA' + '_' + custom_key
        rpc_query_string = '?rpctoken=' + self.token + '&username=' + self.user_name + '&suite=' + aptest_suite_name + '&command=result&sess=' + session_number + '&uuid=' + uuid + '&result=' + result + '&' + execdata + '=' + custom_val + '&note=' + note_default
        rpc_query_string = rpc_query_string.replace('[', '\[')
        rpc_query_string = rpc_query_string.replace(']', '\]')
        rpc_url = 'https://' + self.host + '/run/rpc.mpl' + rpc_query_string
        print("DEBUG: RPC URL is: " + rpc_url + '\n')
        params = ['--connect-timeout', '20', '--silent', '-k']
        params.append(rpc_url)
        try:
            rpc_result_string = subprocess.Popen(['curl'] + params, stdout=subprocess.PIPE).communicate()[0]
            return_string = rpc_result_string.decode('ASCII')
            rpc_result_list = return_string.split('\n')
            rpc_return_value = rpc_result_list[0]
            rpc_return_message = rpc_result_list[1]
            print("DEBUG: RPC result value is: " + rpc_return_value + '\n')
            print("DEBUG: RPC result message is: " + rpc_return_message + '\n')

            return rpc_return_value
        finally:
            print("ERROR: Unable to run rpc query")
            return

    def update_aptest(self):
        num_of_case_uploaded = 0
        aptest_suite_name = "firmware_sonicos"
        while (self.retry):
            if self.get_session_numbers_from_group_id(aptest_suite_name, self.session_group_id):
                self.retry -= 1
                print("hi")
                time.sleep(20)
            else:
                print("success")
                break
        # with open('result.csv', newline='') as f:
        #     reader = csv.DictReader(f)
        #     for result in reader:
        #         # print(row['first_name'], row['last_name'])
        #         if not result['uuid']:
        #             print("INFO: Testcase uuid not defined.  Results not uploaded to ApTest" + '\n')
        #             continue
        #         if result['uuid'] in self.uuid_map:
        #             session_number = self.uuid_map[result['uuid']]
        #             if self.update_results(aptest_suite_name, session_number, **result) == '0':
        #                 num_of_case_uploaded += 1
        #         else:
        #             print("INFO: uuid can't be found in session" + '\n')

# if __name__=="__main__":
#    case = ApTest("alisaauto_1")
#    # case.update_aptest()
#    case.get_session_numbers_from_group_id('firmware_sonicos', 'alisaauto_1')
