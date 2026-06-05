import time, re
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from pyvirtualdisplay import Display
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--headless')

snwl_ip = '10.8.105.164'
snwl_user = 'admin'
snwl_pwd = 'password'

def window_display_hide():
    display = Display(visible=0, size=(1152, 864))
    display.start()

def preempt_check(driver):
    sou_page = driver.page_source
    if len(re.findall('Non-config', sou_page)) > 2:
        driver.find_element_by_name('Continue').click()
    return driver

def system_Login(url_ip, username, password):
    # driver = webdriver.PhantomJS()
    #window_display_hide()
    driver = webdriver.Chrome(chrome_options=chrome_options)
    #print('000000000000000 %s' % url_ip)
    #print('000000000000000 %s' % type(url_ip))
    driver.get('https://' + url_ip + '/auth.html')
    # login_form_location
    driver.switch_to_frame('authFrm')
    driver.find_element_by_name('userName').clear()
    driver.find_element_by_name('userName').send_keys('%s' % username)
    driver.find_element_by_name('pwd').clear()
    driver.find_element_by_name('pwd').send_keys('%s' % password)
    driver.find_element_by_name("Submit").click()
    driver.implicitly_wait(2)
    preempt_check(driver)
    driver.implicitly_wait(3)
    return driver
def switch_class_view(driver):
    driver.switch_to_frame('toggleFrame')
    driver.find_element_by_id('toggleViewBtn').click()
    time.sleep(3)
    return driver
def select_navigation_bar(driver):
    driver.switch_to_frame('outlookFrame')
    driver.find_element_by_link_text('Overview').click()
    driver.find_element_by_link_text('Network').click()
    driver.find_element_by_link_text("Interfaces").click()
    time.sleep(1)
    return driver
def switch_to_pop_window(driver):
    windows = driver.current_window_handle  # 定位当前页面句柄
    all_handles = driver.window_handles  # 获取全部页面句柄
    for handle in all_handles:  # 遍历全部页面句柄
        if handle != windows:  # 判断条件
            driver.switch_to.window(handle)  # 切换到新页面
    '''     
    #diag html.
    with open('aaasum_rst1.html', 'w') as f:
        f.write(driver.page_source)
    interface_source = driver.page_source
    print(type(interface_source))
    '''
    return driver
def wan_mode_check(mode):
    if mode == 'DHCP':
        return 'wanDhcp_iface_ping_mgmt0', 'wanDhcp_iface_ssh_mgmt0', 'dhcp'
    elif mode == 'Static':
        return 'wanStatic_iface_ping_mgmt0', 'wanStatic_iface_ssh_mgmt0', 'static'
    else:
        #print('your FWs ip assignment mode did not march, please selete DHCP or Static ! ')
        return 'none', 'none', 'none'
def quit_windows(driver):
    time.sleep(3)
    driver.quit()
    return driver

def enable_ping_ssh(web_ip, user, pwd):
    driver = system_Login(web_ip, user, pwd)
    driver = switch_class_view(driver)
    driver = select_navigation_bar(driver)

    #open the editInterface_1.html
    driver.switch_to_window(driver.current_window_handle)
    driver.switch_to_frame('tabFrame')
    x1_ip = driver.find_element_by_id('ip_1').text
    print(x1_ip)
    driver.find_element_by_xpath("//a[@href='editInterface_1.html']").click()

    #change the window handles to editinterfae 1
    switch_to_pop_window(driver)

    #check the ip assignment mode
    select_wanmode_type = Select(driver.find_element_by_name('wanMode'))
    print(select_wanmode_type.first_selected_option.text)
    ip_assignment_mode = select_wanmode_type.first_selected_option.text
    wan_iface_ping_mgmt0, wan_iface_ssh_mgmt0, wan_mode = wan_mode_check(ip_assignment_mode)
    if wan_mode == 'none':
        return 'fail', 'none'
    time.sleep(2)
    #get x1 ip address
    #x1_ip = driver.find_element_by_name('wan_iface_static_ip').get_attribute('value')

    #get current ping and ssh status
    ping_status = driver.find_element_by_id('%s' % wan_iface_ping_mgmt0).is_selected()
    ssh_status = driver.find_element_by_id('%s' % wan_iface_ssh_mgmt0).is_selected()
    #print(ping_status)
    #print(type(ping_status))

    #enable ping and ssh
    if ping_status == 0:
        if ssh_status == 0:
            driver.find_element_by_id('%s' % wan_iface_ssh_mgmt0).click()

        driver.find_element_by_id('%s' % wan_iface_ping_mgmt0).click()
        driver.find_element_by_xpath("//input[@class='snwl-btn snwl-btn-primary']").click()
        time.sleep(5)
    elif ping_status == 1:
        if ssh_status == 0:
            driver.find_element_by_id('%s' % wan_iface_ssh_mgmt0).click()
            driver.find_element_by_xpath("//input[@class='snwl-btn snwl-btn-primary']").click()
            time.sleep(5)
        else:
            print('FW had already enabled the ping and ssh, do not need enable it again !')
            driver.find_element_by_xpath("//input[@value='Cancel']").click()
    else:
        print('can not find the element in current page !')

    quit_windows(driver)
    return 'pass', x1_ip
#enable_ping_ssh(snwl_ip, snwl_user, snwl_pwd)