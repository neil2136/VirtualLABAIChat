#coding:utf-8
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from mail_data import MailData

class SendMail(object):
    """
    Define mail format,
    Send Mail method
    """

    def __init__(self):

        self.table_message_summary = """
                                <table class="pure-table">
                                    <thead>
                                        <tr>
                                            <th>ID</th>
                                            <th>Priority</th>
                                            <th>Project</th>
                                            <th>Assignee</th>
                                            <th>Delay</th>
                                            <th>Beta Bloker</th>
                                            <th>Required for Release</th>
                                            <th>Summary</th>
                                    </tr>
                                    </thead>
                                <tbody>

                   """
        self.table_message = """

                           <table class="pure-table">
                               <thead>
                                   <tr>
                                       <th>ID</th>
                                       <th>Priority</th>
                                       <th>Status</th>
                                       <th>Project</th>
                                       <th>Delay</th>
                                       <th>Beta Bloker</th>
                                       <th>Required for Release</th>
                                       <th>Summary</th>
                                   </tr>
                               </thead>
                           <tbody>

              """
        self.head_message = """
           <head>
                <link rel="stylesheet" href="http://yui.yahooapis.com/pure/0.5.0/pure-min.css">
                <style>
                       h2 {
                             color: #d65c00
                        }
                       .pure-table {
                           /* Remove spacing between table cells (from Normalize.css) */
                           border-collapse: collapse;
                           border-spacing: 0;
                           empty-cells: show;
                           border: 2px solid #cbcbcb;
                       }

                       .pure-table caption {
                           color: #000;
                           font: italic 85%/1 arial, sans-serif;
                       }

                       .pure-table td,
                       .pure-table th {
                           border-left: 1px solid #cbcbcb;/*  inner column border */
                           border-right: 1px solid #cbcbcb;/*  inner column border */
                           border-width: 0 0 0 1px;
                           font-size: inherit;
                           margin: 0;
                           overflow: visible; /*to make ths where the title is really long work*/
                           padding: 0.5em 1em; /* cell padding */
                       }

                       /* Consider removing this next declaration block, as it causes problems when
                       there's a rowspan on the first cell. Case added to the tests. issue#432 */
                       .pure-table td:first-child,
                       .pure-table th:first-child {
                           border-left-width: 0;
                       }

                       .pure-table thead {
                        /*   background-color: #e0e0e0;
                           color: #000;*/
                       background-color: #d65c00;
                           color: #FFF;
                           text-align: left;
                           vertical-align: bottom;
                       }

                       /*
                       striping:
                          even - #fff (white)
                          odd  - #f2f2f2 (light gray)
                       */
                       .pure-table td {
                       /*    background-color: transparent;*/
                             background-color: #ffefe2
                       }
                       .pure-table-odd td {
                           background-color: #f2f2f2;
                       }

                       /* nth-child selector for modern browsers
                       .pure-table-striped tr:nth-child(2n-1) td {
                           background-color: #f2f2f2;
                       }*/

                       .pure-table tr {
                           border-bottom: 1px solid #cbcbcb;
                       }
                       .pure-table td {
                           border-bottom: 1px solid #cbcbcb;
                       }
                       </style>
                       </head>
               """

    def send_mail(self, li, DEBUG):
        """
        Receive one mail_list which should be
        [
            ['Terry (Huan) Ding', 'id + p3 + status + delay + summary' ]
        ]
        """
       # msg = MIMEText('you have qa_ready dts to close')
        msg = MIMEMultipart('Alternative')
#        msg_cc = MIMEMultipart('Alternative')
        sender = 'noreply@SonicWALL.com'
        receiver1 = 'qigu@SonicWALL.com'
        s = smtplib.SMTP('10.50.129.54')
        for item in li:
            message = """
            <p>
            Hi %s, <br/><br/>
            Just a kindly reminder, following is the QA_READY or NEED_INFO DTS list that waiting for your feedback, please take a look and follow up ASAP. Thanks!
            </p>""" % item[0].split()[0]
    #        print str(item)
            msg = MIMEText(self.head_message+message+self.table_message+item[1], 'html', 'utf-8')
            msg['From'] = sender
            msg['To'] = MailData.mail_dict[item[0]]
            msg['Cc'] = receiver1
            msg['Subject'] = 'QA DTS Reminder'
            if DEBUG:
                s.sendmail(sender, [receiver1,'qigu@sonicwall.com'], msg.as_string())
                print ('*************')
                print ('mail had send to %s' % receiver1)
            else:
                s.sendmail(sender, [MailData.mail_dict[item[0]],receiver1], msg.as_string())
                print ('*************')
                print ('mail had send to %s' % MailData.mail_dict[item[0]])
        s.quit()


    def send_mail_dev(self, li, DEBUG):
        """
        Receive one mail_list which should be
        [
            ['Terry (Huan) Ding', 'id + p3 + status + delay + summary' ]
        ]
        """
       # msg = MIMEText('you have qa_ready dts to close')
        msg = MIMEMultipart('Alternative')
#        msg_cc = MIMEMultipart('Alternative')
        sender = 'noreply@SonicWALL.com'
        receiver1 = 'qigu@SonicWALL.com'
        s = smtplib.SMTP('10.50.129.54')
        for item in li:
            message = """
            <p>
            Hi %s, <br/><br/>
            Just a kindly reminder, following is the TO_DO DTS list that waiting for your feedback, please take a look and follow up ASAP. Thanks!
            </p>""" % item[0].split()[0]
    #        print str(item)
            msg = MIMEText(self.head_message+message+self.table_message+item[1], 'html', 'utf-8')
            msg['From'] = sender
            msg['To'] = MailData.mail_dict[item[0]]
            msg['Cc'] = receiver1
            msg['Subject'] = 'DEV TODO DTS Reminder'
            if DEBUG:
                s.sendmail(sender, [receiver1,'qigu@sonicwall.com'], msg.as_string())
                print ('*************')
                print ('mail had send to %s' % receiver1)
            else:
                s.sendmail(sender, [MailData.mail_dict[item[0]],receiver1], msg.as_string())
                print ('*************')
                print ('mail had send to %s' % MailData.mail_dict[item[0]])
        s.quit()


    def send_mail_summary(self, content, manager, team):
        msg = MIMEMultipart('Alternative')
        sender = 'noreply@SonicWALL.com'
 #       receiver1 = 'ynan@SonicWALL.com'
        receiver1 = 'qigu@SonicWALL.com'
        s = smtplib.SMTP('10.50.129.54')
        msg = MIMEText(self.head_message+content, 'html', 'utf-8')
        if team == 'QA':
            msg['Subject'] = 'QA DTS Summary'
        else:
            msg['Subject'] = 'DEV DTS Summary'
        msg['From'] = sender
        msg['To'] = manager
        s.sendmail(sender, [manager,'qigu@sonicwall.com'], msg.as_string())
        print ('*********************************')
        print ('mail have already sent to %s' % manager)
        print ('*********************************')
        s.quit()