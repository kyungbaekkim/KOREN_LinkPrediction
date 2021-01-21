######################################################################
## KOREN 링크 인터페이스에서 데이터 수집 및 저장(Batch)             ##
######################################################################
## KOLEN망의 특정 Link(예:광주-대전)에서 과거부터                   ##
## 현재시간까지 누적 된 네트워크 상태정보를 수집하고 MongoDB에 저장 ##
######################################################################

import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import pprint
from datetime import datetime
pd.options.display.float_format = '{:}'.format  # 지수없이 수치값 표현
import persistence.TrafficDAO as TDAO

class TrafficCollector:
    def __init__(self, link):
        ########################
        ## 1.수집할 Link 설정 ##
        ########################
        # link = 'P2-Daejeon-prs1e11-Daejeon-Gwangju'  # 대전 - 광주
        # link = 'P4-Gwangju-prs1e1-Gwangju-Daejeon' # 광주 - 대전
        self.link = link
        self.new_cnt = 0  # 추가된 Traffic 수
        self.url = 'http://168.131.152.62:8000/Interface/{}/hour-minute/'.format(link)  # 수집할 web page URL 생성
        print(self.url)

        # MongoDB
        self.tDao = TDAO.TrafficDAO()

    def web_crawler(self):
        ####################################################
        ## 2.해당 링크에서 데이터 수집(과거부터 현재까지) ##
        ####################################################

        # 2.1 웹 파일 시스템 접속
        try:
            doc = requests.get(self.url)
        except Exception as e:
            print('[ERROR] → Not Found Page:/ ')
            exit()

        # 2.2 웹 파일 시스템에서 docmuent Crawling
        soup = BeautifulSoup(doc.text, 'html.parser')
        csv_list = soup.select('li > a')
        # pprint.pprint(csv_list)

        # 2.3 크롤링 된 페이지에서 원하는 정보만 수집
        #  - 10분단위 데이터(5가지 항목)
        pre_list = []
        # 처음 이전 accumulated 값을 구하기 위한 작업
        df_10min_first = pd.read_csv(self.url + csv_list[0].text)
        previous_accumulated_tx_bytes = df_10min_first['accumulated_tx_bytes'][10]
        previous_accumulated_tx_packets = df_10min_first['accumulated_tx_packets'][10]

        zero_cnt = 0  # 5개의 vector값 중 -값이 나오는 경우 Count
        zero_list = []
        for i, csv_link in enumerate(csv_list[1:]):

            # 10분단위 CSV 파일 Load
            df_10min = pd.read_csv(self.url + csv_link.text)
            # print(df_10min.dtypes)
            pre_csv = dict()

            # print(df_10min['timestamp'][0][-5:])
            hour = df_10min['timestamp'][0][-5:-3]
            minute = df_10min['timestamp'][0][-2:]

            # print('hour → {}'.format(hour))
            # print('min → {}'.format(min))
            print('■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■')
            print('■■', csv_link.text)
            print('[Date] → {}'.format(df_10min['timestamp'][10]))
            str_date = str(df_10min['timestamp'][10])
            pre_csv['date'] = int(str_date[0:4] + str_date[5:7] + str_date[8:10] + str_date[-5:-3] + str_date[-2:])
            print(df_10min['timestamp'][10])
            print('[time_index] → ', (int(hour) * 60) + int(minute))
            pre_csv['time_index'] = (int(hour) * 60) + int(minute)

            # current_tx_packetpersecond의 10분간 평균값 계산
            print('[tx_packetpersecond] → ', df_10min['current_tx_packetpersecond'][:10].mean())
            pre_csv['tx_packetpersecond'] = int(df_10min['current_tx_packetpersecond'][:10].mean())

            # current_tx_bitpersecond의 10분간 평균값 계산
            print('[tx_bitpersecond] → ', df_10min['current_tx_bitpersecond'][:10].mean())
            pre_csv['tx_bitpersecond'] = int(df_10min['current_tx_bitpersecond'][:10].mean())

            # accumulated_tx_bytes의 현재 최신값과 10분 이전의 값의 차이 ex) 11번째 값과 1번째 값의 차이
            print('[tx_bytes] → ', df_10min['accumulated_tx_bytes'][10] - previous_accumulated_tx_bytes)
            pre_csv['tx_bytes'] = int(df_10min['accumulated_tx_bytes'][10] - previous_accumulated_tx_bytes)

            # accumulated_tx_packets의 현재 최신값과 10분 이전의 값의 차이 ex) 11번째 값과 1번째 값의 차이
            print('[tx_packets] → ', df_10min['accumulated_tx_packets'][10] - previous_accumulated_tx_packets)
            pre_csv['tx_packets'] = int(df_10min['accumulated_tx_packets'][10] - previous_accumulated_tx_packets)

            # 1 - Utilization = Bandwidth 허용량, 높을수록 좋음
            # Utilization = tx_bitpersecond / 10G
            print('[link_availability] → ', 1 - (df_10min['current_tx_bitpersecond'][10] / 100000000))
            pre_csv['link_availability'] = 1 - (df_10min['current_tx_bitpersecond'][10] / 100000000)

            # pprint.pprint(pre_csv)

            # 이전 10분 마지막 값을 저장 → 다음 10분에서 차이를 구할 때 사용
            previous_accumulated_tx_bytes = df_10min['accumulated_tx_bytes'][10]
            previous_accumulated_tx_packets = df_10min['accumulated_tx_packets'][10]

            # Vector에서 0보다 작은값 찾기
            vec_list = list(pre_csv.values())[1:6]
            if min(vec_list) < 0:
                zero_cnt += 1
                pre_csv['date'] = df_10min['timestamp'][10]
                zero_list.append(pre_csv)
                continue

            pre_list.append(pre_csv)


        #############################################
        ## 3.수집 된 데이터(과거부터 현재까지) 저장##
        #############################################
        # 3.1 수집 된 데이터 → 판다스 데이터프레임 생성
        df_data = pd.DataFrame(pre_list)  # 10분단위 30개짜리

        # 3.2 수집 된 데이터 → Excel 저장(임시)
        now = datetime.now()
        formattedDate = now.strftime("%Y%m%d")
        output_path = './output/dataset'
        if not os.path.isdir(output_path):
            os.makedirs(output_path)
        df_data.to_excel('./output/dataset/{}_real_traffic.xlsx'.format(self.link), index=False)

        # 3.3 수집 된 데이터 → MongoDB 저장
        for i in pre_list:
            self.tDao.write_real(i)

        ###########################################
        ## 4.수집 결과(과거부터 현재까지) Report ##
        ###########################################
        print('▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒')
        print('▒ Zero List')
        # pprint.pprint(zero_list)
        print('▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒')
        print('▒ [{}] link의 {}건(10분단위) 수집 완료 '.format(self.link, len(pre_list)))
        print('▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒')
        print('▒ 0보다 작은 Vector값은 {} 건 입니다.'.format(zero_cnt))
        print('▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒')
        return len(pre_list)


# collector = TrafficCollector('P5-Daegu-prs2e1-Busan-Daejeon')
# collector.web_crawler()
