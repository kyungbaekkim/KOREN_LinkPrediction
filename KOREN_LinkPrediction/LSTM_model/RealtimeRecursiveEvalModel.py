#####################################
## Bi-LSTM기반 AI 모델 예측 코드   ##
## ==> 10분, 30분, 60분 후를 예측  ##
#####################################

import pprint
from keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
import numpy as np
import pandas as pd
import seaborn as sns
import requests
import json
import matplotlib.pyplot as plt
from datetime import datetime
import persistence.TrafficDAO as TDAO


class RealtimeRecursiveEvalModel:
    def __init__(self, link, new_cnt, flag):
        #################
        ## 1.Data Load ##
        #################
        # 수집 된 Traffic을 포함하여 29개의 이전 Timeseries 데이터 Load => 10분단위 30개 데이터를 기반으로 예측하기 때문!
        if flag == 1:
            self.df_data = pd.read_excel('./output/dataset/{}_real_traffic.xlsx'.format(link))
            self.new_cnt = new_cnt-30  # 새로이 수집된 Traffic 수
        else:
            self.df_data = pd.read_excel('./output/dataset/{}_real_traffic.xlsx'.format(link))[-(new_cnt+29):]
            self.new_cnt = new_cnt  # 새로이 수집된 Traffic 수

        self.df_np_data = self.normalization()
        self.dir_model = './output/model/Bi-LSTM_N30_L3_V5_model_{}.h5'.format(link) # 학습된 모델 저장 경로
        self.model = load_model(self.dir_model) # 학습된 모델 Load

        # Elastic Search 설정
        self.index_link = link.lower()
        # curl -XGET http://localhost:9200/tbl_P2-Daejeon-prs1e11-Daejeon-Gwangju?pretty
        # print('==================================================')
        # print('http://localhost:9200/tbl_{}?pretty'.format(self.index_link))
        # print('==================================================')
        # try:
        #     index_url = 'http://localhost:9200/tbl_{}?pretty'.format(self.index_link)
        #     res = requests.put(index_url)  ####################################
        #     # print("Create Table", link)
        # except Exception as e:
        #     print(e)
        #     print("Exist Table", link)

        # MongoDB 설정
        self.tDao = TDAO.TrafficDAO()

    ##########################
    ## 2.Data Normalization ##
    ##########################
    def normalization(self):
        scaler = MinMaxScaler()
        df_data_normal = self.df_data.copy()
        df_data_normal = df_data_normal.drop(['date', 'link_availability'], axis=1)

        df_data_normal[:] = scaler.fit_transform(df_data_normal[:])
        # df_data_normal.drop(['tx_link_utilization'], axis=1, inplace=True)
        # print(df_data_normal)
        df_np_data = df_data_normal.to_numpy()
        return df_np_data

    ###################################
    ## 4.Generate TRAIN/TEST Dataset ##
    ###################################
    # 현재 10분단위 데이터 30개를 넣고 다음 10분을 예측하는 모델을 위한 데이터셋 생성
    def generateX(self, a, n): # a는 데이터(31, 5), n = 30
        x_train = []
        for i in range(self.new_cnt):  # 31회 반복수행
            x = a[i:(i + n)]
            x_train.append(x)          # 10분단위 1번~30번(30개)

        return np.array(x_train)

    ############################################################
    ## 3.트래픽 예측 모델                                     ##
    ## : 10분, 20분, 30분, 40분, 50분, 60분 Traffic 예측 작업 ##
    ############################################################
    def predictions_model(self):
        X_test = self.generateX(self.df_np_data, 30)
        self.eval_10min_60min(X_test)

    ###############################################
    ## 5.LSTM Model Load and Predict(Multi-Step) ##
    ###############################################
    def eval_10min_60min(self, X_test):
        # 예측된 10분 후 결과를 통해서 10분단위로 20분, 30분, 40분, ~ 계산
        np_eval_10min = np.zeros((self.new_cnt, 5))
        np_eval_20min = np.zeros((self.new_cnt, 5))
        np_eval_30min = np.zeros((self.new_cnt, 5))
        np_eval_40min = np.zeros((self.new_cnt, 5))
        np_eval_50min = np.zeros((self.new_cnt, 5))
        np_eval_60min = np.zeros((self.new_cnt, 5))

        for i in range(len(X_test)): # 1374번 반복 수행
            # X_test[i] → result_10min[i]의 학습 결과 1~30개(10분단위) = 300분
            new_data = X_test[i] # 1~30
            for j in range(6): #
                eval_result = self.model.predict(new_data[-30:].reshape(1, 30, 5)) # 10분단위 예측 → ['time_index', 'tx_packetpersecond', 'tx_bitpersecond', 'tx_bytes', 'tx_packets']

                p_min = (j + 1) * 10

                # print('{}분의 예측결과: {}'.format(p_min, eval_result))
                if p_min == 10:
                    np_eval_10min[i, :] = eval_result
                elif p_min == 20:
                    np_eval_20min[i, :] = eval_result
                elif p_min == 30:
                    np_eval_30min[i, :] = eval_result
                elif p_min == 40:
                    np_eval_40min[i, :] = eval_result
                elif p_min == 50:
                    np_eval_50min[i, :] = eval_result
                elif p_min == 60:
                    np_eval_60min[i, :] = eval_result

                new_data = np.append(new_data, eval_result, axis=0) # TRAIN: 1~30 + PREDICT: 31 = 31

        new_date_list = list(self.df_data['date'][-self.new_cnt:])

        ###############################
        ## 6. Save Prediction Result ##
        ###############################
        # 새로이 추가된 Traffic 수만큼 반복하면서
        # 데이터를 저장 => MongoDB and ElasticSearch
        for i in range(self.new_cnt):
            df_actual = self.df_data[self.df_data['date'] == new_date_list[i]]
            # print(type(df_actual))
            # print(list(df_actual['date'])[0])

            # 6.1 Predictions 결과 ==> ElasticSearch 저장
            # elk_data = {
            #     'log_time': list(df_actual['date'])[0],
            #     'time_index_A': X_test[i][len(X_test[0]) - 1][0],
            #     'tx_packetpersecond_A': X_test[i][len(X_test[0]) - 1][1],
            #     'tx_bitpersecond_A': X_test[i][len(X_test[0]) - 1][2],
            #     'tx_bytes_A': X_test[i][len(X_test[0]) - 1][3],
            #     'tx_packets_A': X_test[i][len(X_test[0]) - 1][4],
            #     'link_usage_A': 1 - (X_test[i][len(X_test[0]) - 1][2] / 100000000),
            #     'time_index_10min': np_eval_10min[i][0],
            #     'tx_packetpersecond_10min': np_eval_10min[i][1],
            #     'tx_bitpersecond_10min': np_eval_10min[i][2],
            #     'tx_bytes_10min': np_eval_10min[i][3],
            #     'tx_packets_10min': np_eval_10min[i][4],
            #     'link_usage_10min': 1 - (np_eval_10min[i][2] / 100000000),
            #     'time_index_30min': np_eval_30min[i][0],
            #     'tx_packetpersecond_30min': np_eval_30min[i][1],
            #     'tx_bitpersecond_30min': np_eval_30min[i][2],
            #     'tx_bytes_30min': np_eval_30min[i][3],
            #     'tx_packets_30min': np_eval_30min[i][4],
            #     'link_usage_30min': 1 - (np_eval_30min[i][2] / 100000000),
            #     'time_index_60min': np_eval_60min[i][0],
            #     'tx_packetpersecond_60min': np_eval_60min[i][1],
            #     'tx_bitpersecond_60min': np_eval_60min[i][2],
            #     'tx_bytes_60min': np_eval_60min[i][3],
            #     'tx_packets_60min': np_eval_60min[i][4],
            #     'link_usage_60min': 1 - (np_eval_60min[i][2] / 100000000)
            # }
            # print('###############################################')
            # print(elk_data)
            # print('###############################################')
            # headers = {'Content-Type': 'application/json; charset=utf-8'}
            # put_url = 'http://localhost:9200/tbl_{index_link}/_doc?pretty'.format(index_link=self.index_link)
            # res = requests.post(put_url, headers=headers, data=json.dumps(elk_data))
            # print('###############################################')
            # print(self.index_link, res.status_code)
            # print('###############################################')

            # 6.2 Predictions 결과 ==> MongoDB 저장
            mongo_data = {'_id' : new_date_list[i],
                    'time_index_A' : self.df_np_data[i][0],
                    'tx_packetpersecond_A' : self.df_np_data[i][1],
                    'tx_bitpersecond_A' : self.df_np_data[i][2],
                    'tx_bytes_A' : self.df_np_data[i][3],
                    'tx_packets_A' : self.df_np_data[i][4],
                    'link_usage_A' : 1-(self.df_np_data[i][2] / 100000000),
                    'time_index_10min': np_eval_10min[i][0],
                    'tx_packetpersecond_10min': np_eval_10min[i][1],
                    'tx_bitpersecond_10min': np_eval_10min[i][2],
                    'tx_bytes_10min': np_eval_10min[i][3],
                    'tx_packets_10min': np_eval_10min[i][4],
                    'link_usage_10min': 1-(np_eval_10min[i][2] / 100000000),
                    'time_index_30min': np_eval_30min[i][0],
                    'tx_packetpersecond_30min': np_eval_30min[i][1],
                    'tx_bitpersecond_30min': np_eval_30min[i][2],
                    'tx_bytes_30min': np_eval_30min[i][3],
                    'tx_packets_30min': np_eval_30min[i][4],
                    'link_usage_30min': 1 - (np_eval_30min[i][2] / 100000000),
                    'time_index_60min': np_eval_60min[i][0],
                    'tx_packetpersecond_60min': np_eval_60min[i][1],
                    'tx_bitpersecond_60min': np_eval_60min[i][2],
                    'tx_bytes_60min': np_eval_60min[i][3],
                    'tx_packets_60min': np_eval_60min[i][4],
                    'link_usage_60min': 1 - (np_eval_60min[i][2] / 100000000)
                    }
            self.tDao.write_predict(mongo_data)
            pprint.pprint(mongo_data)
