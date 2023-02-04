import os
import sys
import time

import requests
import logging
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class Punch:

    def __init__(self):
        self.un = os.environ["SCHOOL_ID"].strip()  # 学号
        logging.info("打卡学号"+self.un)
        self.pd = os.environ["PASSWORD"].strip()  # 密码
        self.SCKey = os.environ["SCKEY"]

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(service=Service(
            '/usr/bin/chromedriver'), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 3, 0.5)

    # 获取本地 SESSIONID
    def login(self):
        try:
            logging.info("正在访问数字杭电")
            self.driver.get("https://cas.hdu.edu.cn/cas/login")
            self.wait.until(EC.presence_of_element_located((By.ID, "un")))
            self.wait.until(EC.presence_of_element_located((By.ID, "pd")))
            self.wait.until(EC.presence_of_element_located(
                (By.ID, "index_login_btn")))
            self.driver.find_element(By.ID, 'un').clear()
            self.driver.find_element(By.ID, 'un').send_keys(self.un)  # 传送帐号
            self.driver.find_element(By.ID, 'pd').clear()
            self.driver.find_element(By.ID, 'pd').send_keys(self.pd)  # 输入密码
            self.driver.find_element(By.ID, 'index_login_btn').click()
        except Exception as e:
            logging.critical("无法访问数字杭电")
            self.wechatNotice("无法访问数字杭电")
            sys.exit(1)

        try:
            self.wait.until(
                EC.presence_of_element_located((By.ID, "errormsg")))
            print("帐号登录失败")
            self.wechatNotice(self.un + "帐号登录失败")
        except TimeoutException as e:
            logging.info("登录成功，正在获取 SESSIONID")
            self.driver.get("https://skl.hduhelp.com/passcard.html#/passcard")
            for retryCnt in range(10):
                time.sleep(1)
                sessionId = self.driver.execute_script(
                    "return window.localStorage.getItem('sessionId')")
                if sessionId is not None and sessionId != '':
                    break
            logging.info(self.send(sessionId))
        finally:
            self.driver.quit()

    # 执行打卡
    def send(self, sessionid):
        logging.info("正在打卡")
        headers = {
            'Content-Type': 'application/json',
            'X-Auth-Token': sessionid,
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 4 XL Build/RQ3A.210705.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/83.0.4103.106 Mobile Safari/537.36 AliApp(DingTalk/5.1.5) com.alibaba.android.rimet/13534898 Channel/212200 language/zh-CN UT4Aplus/0.2.25 colorScheme/light'
        }
        url = "https://skl.hdu.edu.cn/api/punch"
        data = {"currentLocation": "浙江省杭州市钱塘区",
                "healthCode": 0,
                "city": "杭州市",
                "districtAdcode": "330114",
                "province": "浙江省",
                "district": "钱塘区",
                "healthReport": 0,
                "currentLiving": 0,
                "last14days": 0
                }

        for retryCnt in range(3):
            try:
                logging.debug(f"第{retryCnt}次提交表单")
                res = requests.post(
                    url, json=data, headers=headers, timeout=30)
                logging.debug("响应包返回状态：{stat}， 返回内容：{text}".format(
                    stat=res.status_code, text=res.text))
                if res.status_code == 200:
                    self.wechatNotice("打卡成功")
                    return "打卡成功"
                elif retryCnt == 2:
                    logging.critical("提交表单失败,{}".format(res.text))
                    self.wechatNotice("打卡失败，{}".format(res.text))
            except Exception as e:
                if retryCnt < 2:
                    logging.debug(e.__class__.__name__ + "打卡失败，正在重试")
                    time.sleep(3)
                else:
                    logging.error("打卡失败")
                    self.wechatNotice("打卡失败,{}".format(e.__class__.__name__))

    # 打卡失败微信提示
    def wechatNotice(self, message):
        if self.SCKey != '':
            url = 'https://sctapi.ftqq.com/{0}.send'.format(self.SCKey)
            data = {
                'title': message,
            }
            try:
                r = requests.post(url, data=data)
                if r.json()["data"]["error"] == 'SUCCESS':
                    logging.info("微信通知成功")
                else:
                    logging.error("微信通知失败")
            except Exception as e:
                logging.error("{} 推送服务配置错误".format(e.__class__))


logging.basicConfig(level=logging.INFO)
if __name__ == '__main__':
    punch = Punch()
    punch.login()
    logging.info("流程结束")
