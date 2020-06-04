# Imports
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
import json
import datetime
import time      # Delay
import os
# import sys

repeatdelay_sec = 8 * 3600  # 3600sec=1 hour

# Folders/Files setup
# App folder in docker container (/home/seluser/fbevents_app/)
# script_path=os.path.realpath(sys.argv[0]) +"/"
script_path = os.path.dirname(os.path.realpath(__file__))
html_dir = script_path + "fbevents_html/"
paths = {'img': (html_dir + "img/"),
         'newevents': (html_dir + "fbevents_new.txt"),
         'allevents': (html_dir + "fbevents_all.php"),
         'last_dt': (html_dir + "lastscan_dt.txt"),
         'switch': (script_path + "switch_on." + datetime.datetime.now().strftime("%m%d%H%M")),
         'log': (html_dir + "log.txt"),
         'error': (html_dir + "errors.txt")
         }

images_dir = html_dir + "img/"
events_new_file = html_dir + "fbevents_new.txt"
events_all_file = html_dir + "fbevents_all.php"

eventslastscan_file = html_dir + "lastscan_dt.txt"
switch_file = script_path + "switch_on." + \
    datetime.datetime.now().strftime("%m%d%H%M")

log_file = html_dir + "log.txt"
error_file = html_dir + "errors.txt"

###
# Load config from json file:  default.json
with open('./default.json') as json_file:
    config = json.load(json_file)

user1 = config['user1']
site1 = config['site1']

dtnow_str = ""
os.chdir("../")  # Change working dir to parent in favor of selenium( ~ )


# Main
# Single group test
def group_single(user, site):
    driver = init_chromedriver(user, site)
    driver = site_login(driver, user, site)

    # group_handler(driver ,"bluefox.athens" ,"upcoming_events_card" ,"https://www.facebook.com/pg/bluefox.athens/events/?ref=page_internal")
    # group_handler(driver ,"SwingarooZ" ,"upcoming_events_card" ,"https://www.facebook.com/pg/SwingarooZ/events/?ref=page_internal")
    # group_handler(driver ,"rockabillyboogies" ,"upcoming_events_card" ,"https://www.facebook.com/pg/rockabillyboogies/events/?ref=page_internal")
    group_handler(driver, "RhythmHoppers", "upcoming_events_card",
                  "https://www.facebook.com/pg/RhythmHoppers/events/?ref=page_internal")
    driver.quit()


# All groups scan
def groups_all(user, site):
    try:
        driver = init_chromedriver(user, site)
        # driver=login(driver, user ,site)
    except Exception as e:
        logerror("01 (Initializing driver)" + str(e))
        return
    while os.path.exists(switch_file):
        log(" Running events scan")
        filewrite(eventslastscan_file, "w", now_str())  # update last scan file

        # for i in range(len(groups_ar)): # OLD: group_ar
        for group in config['groups']:
            print("Checking:  " + group['name'] + " | " + group['url'])
            try:
                group_handler(
                    driver, group['name'], "upcoming_events_card", group['url'])
            except Exception as e:
                logerror("02 (handler error) " +
                         group['name'] + "\n" + str(e))
                try:
                    driver.get_screenshot_as_file(
                        images_dir + group['name'] + '.png')
                except Exception:
                    logerror("03 (can't save error screenshot) " +
                             group['name'] + "\n" + str(e))
                time.sleep(10)  # delay between groups 10 sec
        log("\n\n### Job finished!\n" + "### Sleeping for: " +
            str(repeatdelay_sec) + " sec ")
        time.sleep(repeatdelay_sec)  # 2 hours
    driver.quit()


# Repeater
repeatdelay = "minutes=15"  # "weeks=40, days=84, hours=23, minutes=50, seconds=600"
checkdelay_sec = 300  # 5 min (3600sec=1 hour)
# switch_file="/home/seluser/fbevents_app/scheduler.on"


def repeater(user, site):
    task1next_dt = datetime.datetime.now()
    while True:
        if(not os.path.exists(switch_file)):
            log("\n" + now_str() + "   ### SCHEDULER - SWITCH FILE EXIT:")
            return

        print("Next task 1 run: " + task1next_dt.strftime("%Y-%m-%d %H:%M"))
        if datetime.datetime.now() >= task1next_dt:
            task1next_dt = datetime.datetime.now() + datetime.timedelta(minutes=15)  # (hours=1)
            log("\n" + now_str() + "  Running task 1: ")
            # Task1:
            groups_all(user, site)
        time.sleep(checkdelay_sec)  # 5 min (3600sec=1 hour)


# # Firefox
# def init_firefoxdriver():
#    driver = webdriver.Firefox()
#    driver.wait = WebDriverWait(driver, 5)
#    return driver


def init_chromedriver(user, site):
    """  Init chrome ( PROXY = "88.157.149.250:8080" # IP:PORT or HOST:PORT ) 
    USE: init_chromedriver("88.157.149.250:8080", "selenium") """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    if user['proxy'] != "":
        chrome_options.add_argument(
            '--proxy-server=%s' % user['proxy'])   # Set proxy
    if user['userdirectory'] != "":
        chrome_options.add_argument("user-data-dir=" + user['userdirectory'])
    chrome_options.binary_location = '/usr/bin/google-chrome'
    driver = webdriver.Chrome(executable_path=os.path.abspath(
        "chromedriver"), chrome_options=chrome_options)
    driver.maximize_window()
    return driver


def site_login(driver, user, site):
    """ Login to site. USE:  login(driver ,'user1', 'site1') """

    if cookieTest(driver, site1):
        return driver

    driver.get(site['login_url'])
    print("# Title: " + driver.title)
    assert "Facebook" in driver.title
    elem = driver.find_element_by_id(site['login_id'])
    elem.send_keys(user['username'])
    elem = driver.find_element_by_id(site['pass_id'])
    elem.send_keys(user['password'])
    elem.send_keys(Keys.RETURN)

    return driver


def cookieTest(driver, site):
    """ Check if already logged in. USE: res = cookieTest(driver ,site1) """
    driver.get(site['start_url'])
    items = driver.find_elements_by_tag_name(site['checklogid'])
    if items:
        print('# Not logged in')
        return False
    return True


def group_handler(driver, group_name, element_name, group_url):
    """ Handler that scrapes all groups """
    dtnow_str = now_str()

    driver.get(group_url)
    time.sleep(5)
    print("  Title: " + driver.title)
    driver.get_screenshot_as_file(images_dir + 'fb.png')

    # try:
    #     assert "Facebook" in driver.title  # RhythmHoppers fails this
    # except Exception as e:
    #     logerror( group_name +"  Assert missmatch: " +"\n" +str(e))
    # return

    html_list = driver.find_element_by_id(element_name)
    items = html_list.find_elements_by_tag_name("tr")
    print("  Items: " + str(len(items)))

    for item in items:
        # print("# Item: " +item.text)
        item_ar = item.text.split('\n')
        item_date = item_ar[1] + "  " + item_ar[0]
        item_time = item_ar[3]
        pos = item_time.find(" · ")
        item_guests = item_time[(pos + 3):]
        item_time = item_time[:pos]

        if '-' in item_time:
            tmp = item_time.split(' - ')
            itemstart = tmp[0]
            itemend = tmp[1]
        else:
            item_time = item_time.split(". ")[1]
            item_time = item_time.split(" UTC")[0]
            itemstart = item_date + " " + item_time
            itemend = ""
            itemstart = translate(itemstart)
            itemstart_dt = datetime.datetime.strptime(
                "2019 " + itemstart, "%Y %d  %b %H:%M")
            itemstart = itemstart_dt.strftime("%Y-%m-%d %H:%M")

        link = item.find_element_by_tag_name('a')
        if not link:
            linklong_url = item_text = item_url = pos = item_id = button = ""
        if link:
            linklong_url = link.get_attribute("href")
            pos = linklong_url.find("?")
            item_text = link.text
            item_url = linklong_url[0:pos]
            pos = item_url.find("/events/") + 8
            item_id = item_url[pos:-1]
            button = '<button type="submit" name="name1" value="' + item_id + '">NEW</button>'
        print("  " + item_text + "| " + item_url + "| " + item_guests)
        # event=item_date +"|" +item_time +"|" +group_name +"|" +item_text +"| " +item_url +" |" +item_guests
        # event = item_date +"|" +item_time +"|" +group_name +" : "  +'<a href="' +item_url +'">'  +item_text  +"</a>"
        event = itemstart + "|" + itemend + "|" + group_name + \
            " : " + '<a href="' + item_url + '">' + item_text + "</a>"
        res = filewriteifnotexist(events_all_file, item_url, event + "<br>\n")
        if res:
            eventcontrol = button + event + "|" + \
                item_guests + "|" + "scan time: " + dtnow_str
            res = filewriteifnotexist(
                events_new_file, item_url, eventcontrol + "<br>\n")
            log("### Event Added: " + item_text + "| " + item_url)


# Library
def now_str():
    """ now  """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
#  return datetime.datetime.now().strftime("%m-%d %H:%M")


def log(print_str):
    """ log
    # log_file=html_dir+"log.txt"
    # error_file=html_dir+"errors.txt"
    """
    print_str = now_str() + " " + print_str + "\n"
    print(print_str)
    filewrite(log_file, "a", print_str)


def logerror(print_str):
    """ logerror  """
    print_str = "\n" + now_str() + " ### Error: " + print_str + "\n"
    print(print_str)
    filewrite(log_file, "a", print_str)
    filewrite(error_file, "a", print_str)


def filewriteifnotexist(data_file, search_str, add_str):
    """ use:  filewriteifnotexist("eventsoutput.txt" ,"asdf" ,"asdf-add") """
    data_str = ""
    res = False
    try:
        f = open(data_file, "r")
        data_str = f.read()
    except Exception as e:
        print("\nerror: " + str(e))
    if search_str not in data_str:
        data_str = add_str + data_str
        f = open(data_file, "w")
        f.write(data_str)
        res = True
    f.close()
    return res


def filewrite(spec_file, mode, text):
    """ (a:add ,w:new) filewrite(logerror_file, mode, '\nError: ') """
    with open(spec_file, mode) as write_file:
        write_file.write(text)


def translate(spec_str):
    """use: translate('2019 28  MAI 13:00') """
    germantranslate = {'MRZ': 'MAR', 'MAI': 'MAY', 'OKT': 'OCT', 'DEZ': 'DEC'}
    for key, val in germantranslate.items():
        spec_str = spec_str.replace(key, val)
    return spec_str


# Startup
if __name__ == "__main__":
    filewrite(switch_file, "w", ' ')

    # repeater()
    groups_all(user1, site1)
    # group_single(user1, site1) # "178.128.223.53:8080")
