#coding:utf-8
import requests
from bs4 import BeautifulSoup
from mail_data import MailData
from sendmail import SendMail
import datetime
import os

SV_PASSWD=os.environ.get('SV_PASSWD')
print(SV_PASSWD)
class JiraDts(object):

    def __init__(self):
        self.user = 'qigu'
        self.passwd = SV_PASSWD
        self.url = "https://track.eng.sonicwall.com/"

    def login(self):
        login_data = {
            'os_username' : self.user,
            'os_password' : self.passwd,
        }

        session = requests.post(self.url + 'login.jsp',
                                data=login_data, verify=False)
        sess = session.headers['Set-Cookie']
        session_id = sess.split(';')[0]+'; '+ sess.split(';')[2][10:]
        print ("session_id= %s" %session_id)
        return session_id


    def result_needinfo(self, num, session_id, platform):
        print(num)
        headers = {'Cookie': session_id}
        month_dic = {
            'Jan': '1','Feb': '2','Mar': '3','Apr':'4','May':'5','Jun':'6',
            'Jul':'7','Aug':'8','Sep':'9','Oct':'10','Nov':'11','Dec':'12',

        }
        d1 = datetime.datetime.now()
        result_item = []                      # [[name, id,priority,status,project, days,],]
        result_item_summary = []              # [[name, id, priority, name, days, summary],]
        for i in range(0, num, 50):
            url = self.url + 'issues/%s&startIndex=%d' % (platform, i/50*50)
            print (url)
            response = requests.get(url, headers=headers, verify=False)
            soup = BeautifulSoup(response.content, 'html.parser')
            print(soup.prettify())
            result = []
            td_list = soup.find_all("tr")         # [<tr><th></th></tr>,<tr><td></td></tr>,...]
            #print(td_list)
            print(td_list[0])
            result = td_list[1:]                  # the first <tr> is <th> not <td>
            print(result[0])

            for item in result:
                d2 = item.find_all("td")[6].time.string
                d2_list = d2.split('/')
                d2_string = '20'+d2_list[2]+'-'+month_dic[d2_list[1]]+'-'+d2_list[0]
                d2 = datetime.datetime.strptime(d2_string, "%Y-%m-%d")
                try:
                    result_item.append([
                        item.find_all("td")[5].a.string,        # name
                        "<a href=https://track.eng.sonicwall.com/browse/%s>%s</a>" % (item.find_all("td")[0].a['data-issue-key'],item.find_all("td")[0].a['data-issue-key']),
                        item.find_all("td")[3].img['alt'],      # priority
                        item.find_all("td")[4].span.string,     # status
                        (item.find_all("td")[8].a.string).strip(),          # projects
                        str((d1-d2).days)+' days',              # days
                        str(item.find_all("td")[10].string),     # Beta blocker
                        str(item.find_all("td")[11].font.string),     # require for release
                        item.find_all("td")[1].a.string,        # summary
                    ])
                    result_item_summary.append([
                        item.find_all("td")[5].a.string,        # name
                        "<a href=https://track.eng.sonicwall.com/browse/%s>%s</a>" % (item.find_all("td")[0].a['data-issue-key'],item.find_all("td")[0].a['data-issue-key']),
                        item.find_all("td")[3].img['alt'],      # priority
                        (item.find_all("td")[8].a.string).strip(),          # projects
                        item.find_all("td")[5].span.string,     # QA Assignee
                        str((d1-d2).days)+' days',
                        str(item.find_all("td")[10].string),     # Beta blocker
                        str(item.find_all("td")[11].font.string),     # require for release
                        item.find_all("td")[1].a.string,        # summary
                    ])
                except:
                    result_item.append([
                        item.find_all("td")[5].a.string,        # name
                        "<a href=https://track.eng.sonicwall.com/browse/%s>%s</a>" % (item.find_all("td")[0].a['data-issue-key'],item.find_all("td")[0].a['data-issue-key']),
                        item.find_all("td")[3].img['alt'],      # priority
                        item.find_all("td")[4].span.string,     # status
                        (item.find_all("td")[8].a.string).strip(),          # projects
                        str((d1-d2).days)+' days',              # days
                        str(item.find_all("td")[10].string),     # Beta blocker
                        str(item.find_all("td")[11].string),     # require for release
                        item.find_all("td")[1].a.string,        # summary
                    ])
                    result_item_summary.append([
                        item.find_all("td")[5].a.string,        # name
                        "<a href=https://track.eng.sonicwall.com/browse/%s>%s</a>" % (item.find_all("td")[0].a['data-issue-key'],item.find_all("td")[0].a['data-issue-key']),
                        item.find_all("td")[3].img['alt'],      # priority
                        (item.find_all("td")[8].a.string).strip(),          # projects
                        item.find_all("td")[5].span.string,     # QA Assignee
                        str((d1-d2).days)+' days',
                        str(item.find_all("td")[10].string),     # Beta blocker
                        str(item.find_all("td")[11].string),     # require for release
                        item.find_all("td")[1].a.string,        # summary
                    ])
        return (result_item, result_item_summary)

    def get_num(self, session_id, platform):
        headers = {'Cookie': session_id}
        url = self.url + 'issues/%s' %platform
        print (url)
        response = requests.get(url, headers=headers, verify=False)
#        print response.content
        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            number = soup.find_all("span", class_="results-count-total results-count-link")
            num = int(number[0].string)
        except:
            num = 0
        return num

    def result_qaready(self, num, session_id, platform):
        print(num)
        headers = {'Cookie': session_id}
        result_item = []
        result_item_summary = []
        month_dic = {
            'Jan': '1', 'Feb': '2', 'Mar': '3', 'Apr':'4', 'May': '5',
            'Jun': '6', 'Jul': '7', 'Aug': '8', 'Sep': '9', 'Oct': '10',
            'Nov': '11', 'Dec': '12',

        }
        d1 = datetime.datetime.now()
        for i in range(0, num, 50):
            url = self.url + 'issues/%s&startIndex=%d' %(platform, i/50*50)
            print (url)
            response = requests.get(url, headers=headers, verify=False)
#            print response.content
            soup = BeautifulSoup(response.content, 'html.parser')
            td_list = soup.find_all("tr")
#            print(td_list[0])
            result = td_list[1:]
            for item in result:
                d2 = item.find_all("td")[6].time.string           # '15/Jul/18'
                d2_list = d2.split('/')                           # [15,Jul,18]
                d2_string = '20'+d2_list[2]+'-'+month_dic[d2_list[1]]+'-'+d2_list[0] # '2018-7-15'
                print(d2_string)
                d2 = datetime.datetime.strptime(d2_string, "%Y-%m-%d")
                try:
                    result_item.append([
                        item.find_all("td")[5].a.string,        # name
                        "<a href=https://track.eng.sonicwall.com/browse/%s>%s</a>" % (item.find_all("td")[0].a['data-issue-key'],item.find_all("td")[0].a['data-issue-key']),
                        item.find_all("td")[3].img['alt'],      # priority
                        item.find_all("td")[4].span.string,     # status
                        (item.find_all("td")[8].a.string).strip(),          # projects
                        str((d1-d2).days)+' days',              # days
                        str(item.find_all("td")[10].string),     # Beta blocker
                        str(item.find_all("td")[11].font.string),     # require for release
                        item.find_all("td")[1].a.string,        # summary
                    ])
                    result_item_summary.append([
                        item.find_all("td")[5].a.string,        # name
                        "<a href=https://track.eng.sonicwall.com/browse/%s>%s</a>" % (item.find_all("td")[0].a['data-issue-key'],item.find_all("td")[0].a['data-issue-key']),
                        item.find_all("td")[3].img['alt'],      # priority
                        (item.find_all("td")[8].a.string).strip(),          # projects
                        item.find_all("td")[5].span.string,     # QA Assignee
                        str((d1-d2).days)+' days',
                        str(item.find_all("td")[10].string),     # Beta blocker
                        str(item.find_all("td")[11].font.string),     # require for release
                        item.find_all("td")[1].a.string,        # summary
                    ])
                except:
                    result_item.append([
                        item.find_all("td")[5].a.string,        # name
                        "<a href=https://track.eng.sonicwall.com/browse/%s>%s</a>" % (item.find_all("td")[0].a['data-issue-key'],item.find_all("td")[0].a['data-issue-key']),
                        item.find_all("td")[3].img['alt'],      # priority
                        item.find_all("td")[4].span.string,     # status
                        (item.find_all("td")[8].a.string).strip(),          # projects
                        str((d1-d2).days)+' days',              # days
                        str(item.find_all("td")[10].string),     # Beta blocker
                        str(item.find_all("td")[11].string),     # require for release
                        item.find_all("td")[1].a.string,        # summary
                    ])
                    result_item_summary.append([
                        item.find_all("td")[5].a.string,        # name
                        "<a href=https://track.eng.sonicwall.com/browse/%s>%s</a>" % (item.find_all("td")[0].a['data-issue-key'],item.find_all("td")[0].a['data-issue-key']),
                        item.find_all("td")[3].img['alt'],      # priority
                        (item.find_all("td")[8].a.string).strip(),          # projects
                        item.find_all("td")[5].span.string,     # QA Assignee
                        str((d1-d2).days)+' days',
                        str(item.find_all("td")[10].string),     # Beta blocker
                        str(item.find_all("td")[11].string),     # require for release
                        item.find_all("td")[1].a.string,        # summary
                    ])

        return (result_item, result_item_summary)


    def result_todo(self,num, session_id, platform):
        """
        https://track.eng.sonicwall.com/issues/?filter=11429
        which is search todo filter item
        return result and result_summary

        """
        print(num)
        headers = {'Cookie': session_id}
        result_item = []
        result_item_summary = []
        month_dic = {
            'Jan': '1','Feb': '2','Mar': '3','Apr':'4','May':'5','Jun':'6',
            'Jul':'7','Aug':'8','Sep':'9','Oct':'10','Nov':'11','Dec':'12',

        }
        d1 = datetime.datetime.now()
        for i in range(0,num,50):
            url = self.url + 'issues/%s&startIndex=%d' %(platform, i/50*50)
            print(url)
            response = requests.get(url, headers=headers, verify=False)
#            print response.content
            soup = BeautifulSoup(response.content, 'html.parser')
            td_list = soup.find_all("tr")
#            print(td_list[0])
            result = td_list[1:]
            for item in result:
                d2 = item.find_all("td")[6].time.string           # '15/Jul/18'
                d2_list = d2.split('/')                           # [15,Jul,18]
                d2_string = '20'+d2_list[2]+'-'+month_dic[d2_list[1]]+'-'+d2_list[0] # '2018-7-15'
                print (d2_string)
                d2 = datetime.datetime.strptime(d2_string, "%Y-%m-%d")
                if (d1-d2).days > 3:
                    try:
                        name = item.find_all("td")[2].a.string
                    except:
                        name = 'None'
                    try:
                        require = item.find_all("td")[11].font.string
                    except:
                        require = item.find_all("td")[11].string

                    result_item.append([
                       name,            # Assignee
                       "<a href=https://track.eng.sonicwall.com/browse/%s>%s</a>" % (item.find_all("td")[0].a['data-issue-key'],item.find_all("td")[0].a['data-issue-key']),
                       item.find_all("td")[3].img['alt'],
                       item.find_all("td")[4].span.string,
                       item.find_all("td")[8].a.string.strip(),          # projects
                       str((d1-d2).days)+' days',
                       item.find_all("td")[10].string,     # Beta blocker
                       require,     # require for release
                       item.find_all("td")[1].a.string,
                   ])
                    result_item_summary.append([
                       name,        # name
                       "<a href=https://track.eng.sonicwall.com/browse/%s>%s</a>" % (item.find_all("td")[0].a['data-issue-key'],item.find_all("td")[0].a['data-issue-key']),
                       item.find_all("td")[3].img['alt'],      # priority
                       (item.find_all("td")[8].a.string).strip(),          # projects
                       name,     # Assignee
                       str((d1-d2).days)+' days',     # delay
                       item.find_all("td")[10].string,     # Beta blocker
                       require,     # require for release
                       item.find_all("td")[1].a.string,        # summary
                   ])
        return (result_item, result_item_summary)


    def result_filter(self, raw_result):
        """
        some result belong to dev
        filter QA member in raw_result
        """
        qa2_list = []
        qa3_list = []
        system_qa_list = []
        for item in raw_result:
            if item[0] in MailData.qa_2_mail_dict.keys():
                qa2_list.append(item)
            elif item[0] in MailData.system_mail_dict.keys():
                system_qa_list.append(item)
            elif item[0] in MailData.qa_3_mail_dict.keys():
                qa3_list.append(item)
        return (qa2_list,qa3_list,system_qa_list)


    def result_filter_dev(self, raw_result):
        """
        some result belong to dev
        filter QA member in raw_result
        """
        zhong_list = []
        eric_list = []
        david_list = []
        bruce_list = []
        shawndon_list = []
        for item in raw_result:
            if item[0] in MailData.zhong_mail_dict.keys():
                zhong_list.append(item)
            elif item[0] in MailData.bruce_mail_dict.keys():
                bruce_list.append(item)
            elif item[0] in MailData.david_mail_dict.keys():
                david_list.append(item)
            elif item[0] in MailData.shawndon_mail_dict.keys():
                shawndon_list.append(item)
            elif item[0] in MailData.eric_mail_dict.keys():
                eric_list.append(item)
        return (zhong_list, eric_list, david_list, bruce_list, shawndon_list)



    def result_filter_platform(self, team_list, platform):
        """
        filter team_list DTS by platform
        """
        result = []
        for item in team_list:
            if item[3] == platform:
                result.append(item)
        return result


    def release_category(r):
        """
           content of recorde
           final_mail_list = [
                                ['hding','ID+pri+status+days+summary'],
                                ['allen','ID+pri+status+days+summary'],
                                ...
                            ]
        """
        mail_list = []
        send_mail = SendMail()
        r = sorted(r, key=lambda x:str(x[3]))
        for item in r:
            item[1] = str(item[1])
            item[2] = str(item[2])
            item[3] = str(item[3])
            item[4] = str(item[4])
            item[5] = str(item[5])
            item[6] = str(item[6])
            item[7] = str(item[7])
            item[8] = str(item[8])
            mail_list.append([item[0], '<tr><td>'+item[1]+'</td>' +
                              '<td>'+item[2]+'</td>' +
                              '<td>'+item[3]+'</td>' +
                              '<td>'+item[4]+'</td>' +
                              '<td>'+item[5]+'</td>' +
                              '<td>'+item[6]+'</td>' +
                              '<td>'+item[7]+'</td>' +
                              '<td>'+item[8]+'</td></tr>'])

        for i in mail_list:
            for j in mail_list[(mail_list.index(i)+1):]:
                if i[0] == j[0]:
                    i[1] += '<br/>'+j[1]
                    mail_list.remove(j)
        return mail_list

    def release_category_summary(todo, qa_ready, needinfo):
        """
        content of qa_ready recordes + content of needinfo recordes
        """
        send_mail = SendMail()
        content = ''
        if todo:
            todo_summary = '<h3 align="center">%s TODO Records Displayed</h3>'\
                           % str(len(todo)) + '<hr/>' + \
                           send_mail.table_message_summary
            content += todo_summary
            for item in todo:
                item[1] = str(item[1])
                item[2] = str(item[2])
                item[3] = str(item[3])
                item[4] = str(item[4])
                item[5] = str(item[5])
                item[6] = str(item[6])
                item[7] = str(item[7])
                item[8] = str(item[8])
                content += ('<tr><td>'+item[1]+'</td>' +
                            '<td>'+item[2]+'</td>' +
                            '<td>'+item[3]+'</td>' +
                            '<td>'+item[4]+'</td>' +
                            '<td>'+item[5]+'</td>' +
                            '<td>'+item[6]+'</td>' +
                            '<td>'+item[7]+'</td>' +
                            '<td>'+item[8]+'</td></tr>')

            content += '</tbody></table>'

        if needinfo:
            needinfo_summary = '<h3 align="center">%s NEEDINFO Records Displayed</h3>' % str(len(needinfo))+'<hr/>'+ send_mail.table_message_summary
            content += needinfo_summary
            needinfo = sorted(needinfo, key=lambda x:str(x[7]), reverse=True)
            for item in needinfo:
                item[1] = str(item[1])
                item[2] = str(item[2])
                item[3] = str(item[3])
                item[4] = str(item[4])
                item[5] = str(item[5])
                item[6] = str(item[6])
                item[7] = str(item[7])
                item[8] = str(item[8])
                content += ('<tr><td>'+item[1]+'</td>' +
                            '<td>'+item[2]+'</td>' +
                            '<td>'+item[3]+'</td>' +
                            '<td>'+item[4]+'</td>' +
                            '<td>'+item[5]+'</td>' +
                            '<td>'+item[6]+'</td>' +
                            '<td>'+item[7]+'</td>' +
                            '<td>'+item[8]+'</td></tr>')

            content += '</tbody></table>'
        if qa_ready:
            qa_ready_summary = '<h3 align="center">%s QA_READY Records Displayed</h3><hr/>' % str(len(qa_ready)) + send_mail.table_message_summary
            content += qa_ready_summary
            qa_ready = sorted(qa_ready, key=lambda x:str(x[7]), reverse=True)
            for item in qa_ready:
                item[1] = str(item[1])
                item[2] = str(item[2])
                item[3] = str(item[3])
                item[4] = str(item[4])
                item[5] = str(item[5])
                item[6] = str(item[6])
                item[7] = str(item[7])
                item[8] = str(item[8])
                content += ('<tr><td>'+item[1]+'</td>' +
                              '<td>'+item[2]+'</td>' +
                              '<td>'+item[3]+'</td>' +
                              '<td>'+item[4]+'</td>' +
                              '<td>'+item[5]+'</td>' +
                              '<td>'+item[6]+'</td>' +
                              '<td>'+item[7]+'</td>' +
                              '<td>'+item[8]+'</td></tr>')

            content += '</tbody></table>'
        return content


if __name__ == '__main__':

    jiradts = JiraDts()
    sessid = jiradts.login()
    url = ('?jql=project%20in%20' +
                    '("Gen7"%2C%20' +
                    '"Next%20Gen%20Policy%20Engine"%2C%20' +
                    '"NSSP"%2C%20' +
                    '"Gen6"%2C%20' +
                    '"Wireless%20SonicCloud"%2C%20' +
                    '"SonicOSV")' +
                    '%20AND%20issuetype%20in%20("Bug%20DTS")%20AND%20' +
                    'status%20in%20("Need%20Info")' +
                    '%20AND%20"QA%20Assignee"%20in%20' +
                    '(ynan%2C%20 ywei%2C%20ldu%2C%20rhu%2C%20mma%2C%20' +
                    'jlian%2C%20dhuang%2C%20hxu%2C%20nizhang%2C%20' +
                    'czhao%2C%20juliu%2C%20hding%2C%20pcao%2C%20pzhou%2C%20' +
                    'qshi%2C%20hhua%2C%20yhua%2C%20khuang%2C%20jwu%2C%20' +
                    'zye%2C%20xzhou%2C%20jnzhang%2C%20cyuan%2C%20xhu%2C%20' +
                    'xuwang%2C%20fhuang%2C%20rmeng%2C%20xyu%2C%20' +
                    'lezhang%2C%20lbian%2C%20mguo%2C%20xpeng%2C%20' +
                    'ykang%2C%20wmao%2C%20xzhan%2C%20vding%2C%20fxia%2C%20jrxiong%2C%20' +
                    'ywen%2C%20luli%2C%20rwei%2C%20jyuan%2C%20whuang%2C%20' +
                    'yili%2C%20yhou%2C%20 wgong%2C%20 rshang%2C%20' +
                    'cxu%2C%20jxu%2C%20bychen%2C%20cdai%2C%20flv)'
                    )
    a, b = jiradts.result_needinfo(10, sessid, url)
    print(b[0])