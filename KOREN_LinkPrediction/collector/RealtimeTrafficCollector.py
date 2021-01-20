######################################################################
## KOREN 링크 인터페이스에서 데이터 수집 및 저장(Real-Time)         ##
######################################################################
## KOLEN망의 특정 Link(예:광주-대전)에서 실시간(10분단위)으로       ##
## 네트워크 상태정보를 수집하고 MongoDB에 저장                      ##
######################################################################

import requests
from bs4 import BeautifulSoup
import pandas as pd
import pprint
from datetime import datetime
import persistence.TrafficDAO as TDAO

pd.options.display.float_format = '{:}'.format  # 지수없이 수치값 표현


class RealtimeTrafficCollector:

    def __init__(self, link):
        ########################
        ## 1.수집할 Link 설정 ##
        ########################
        # link = 'P2-Daejeon-prs1e11-Daejeon-Gwangju'  # 대전 - 광주
        # link = 'P4-Gwangju-prs1e1-Gwangju-Daejeon' # 광주 - 대전
        self.tDao = TDAO.TrafficDAO()
        self.link = link
        self.new_cnt = 0 # 추가된 Traffic 수
        self.url = 'http://168.131.152.62:8000/Interface/{}/hour-minute/'.format(link) # 수집할 web page URL 생성

        # MongoDB
        self.tDao = TDAO.TrafficDAO()

        # 처음 시작하는 경우 기존 Excel값이 없기 때문에 빈칸으로 채우기
        try:
            self.df_real = pd.read_excel('./output/dataset/{}_real_traffic.xlsx'.format(link))
        except Exception as e:
            print(e)
            self.df_real = []

    def traffic_collector(self, csv_list, new_cnt):
        new_traffic_list = []

        # 처음 이전 accumulated 값을 구하기 위한 작업
        df_10min_first = pd.read_csv(self.url + csv_list[-(new_cnt+1)].text)
        previous_accumulated_tx_bytes = df_10min_first['accumulated_tx_bytes'][10]
        previous_accumulated_tx_packets = df_10min_first['accumulated_tx_packets'][10]

        zero_cnt = 0  # 5개의 vector값 중 -값이 나오는 경우 Count
        zero_list = []
        for i, csv_link in enumerate(csv_list[-new_cnt:]):
            # print('[수집하는 LINK excel 파일] => {}'.format(csv_link))
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

            # # tx_link_utilization의 10분간 평균값 계산
            # print('[tx_link_utili'
            #       'zation] → ', df_10min['tx_link_utilization'][:10].mean())
            # pre_csv['tx_link_utilization'] = df_10min['tx_link_utilization'][:10].mean()

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

            new_traffic_list.append(pre_csv)

            # 3.1 수집 된 데이터 → MongoDB 저장
            for i in new_traffic_list:
                self.tDao.write_real(i)

        return new_traffic_list

    def realtime_crawler(self):
        ##################################################
        ## 2.해당 링크에서 실시간(10분단위) 데이터 수집 ##
        ##################################################

        # 2.1 웹 파일 시스템 접속
        try:
            doc = requests.get(self.url)
        except Exception as e:
            print('[ERROR] → Not Found Page:/ ')
            exit()

        # 2.2 웹 파일 시스템에서 docmuent Crawling
        soup = BeautifulSoup(doc.text, 'html.parser')
        csv_list = soup.select('li > a')

        # 2.2 조건부 이벤트
        #  - 실시간 수집 결과 변동된 사항이 있는지 체크
        # 기존 수집된 Traffic 수와 web page의 Traffic 수를 비교하여 변동됐으면 동작!
        len_save_data = len(self.df_real)
        len_new_data = len(csv_list)
        print('[INFO] SAVE DATA LENGTH => {}'.format(len_save_data)) # 해당 Link의 저장된 Traffic 개수
        print('[INFO] NEW DATA LENGTH => {}'.format(len_new_data))   # 해당 Link의 Web(FileSystem)의 Traffic 개수

        # 2.3 이벤트가 발생하면 데이터 수집
        #  - 10분단위 데이터(5가지 항목)
        #  - 새로운 트래픽 데이터 추가됨 => 이벤트 발생
        if len_new_data > len_save_data: # web의 Traffic 개수가 많다는 뜻은 Traffic data update를 의미
            self.new_cnt = int(len_new_data - len_save_data)

            # 해당 Link의 새롭게 추가된 Traffic 데이터 수집 => new_traffic_list => 구조: [{}, {}, {}, {}, {}, {}]
            new_traffic_list = self.traffic_collector(csv_list, self.new_cnt)



            # 새롭게 수집된 Traffic을 데이터프레임에 추가(기존 Traffic + 수집된 Traffic)
            for new_traffic in new_traffic_list:
                # print(new_traffic)
                self.df_real = self.df_real.append(new_traffic, ignore_index=True)

            #############################################
            ## 3.수집 된 데이터(과거부터 현재까지) 저장##
            #############################################
            # 3.2 수집 된 데이터 → Excel 저장(임시)
            # Traffic 엑셀 데이터 동기화 => 데이터프레임(기존 Traffic + 수집된 Traffic)을 업로드
            self.df_real.to_excel('./output/dataset/{}_real_traffic.xlsx'.format(self.link), index=False)
            return 1, self.new_cnt
        else:
            return 0, self.new_cnt

# collector = RealtimeTrafficCollector('P2-Daejeon-prs1e11-Daejeon-Gwangju')
# collector.realtime_crawler()
