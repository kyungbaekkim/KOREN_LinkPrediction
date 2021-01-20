#######################################
## Bi-LSTM기반 AI 모델 학습하는 코드 ##
#######################################

import os
import pandas as pd
import numpy as np
from keras.layers.core import Dense, Dropout
from keras.layers.normalization import BatchNormalization
from keras.layers.recurrent import LSTM
from keras.layers import Bidirectional
from keras.models import Sequential
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
from keras.utils.multi_gpu_utils import multi_gpu_model


class GenAI10Min:
    def __init__(self, link):
        #################
        ## 1.Data Load ##
        #################
        # link = 'P4-Gwangju-prs1e1-Gwangju-Daejeon'
        self.link = link # 'P5-Daegu-prs2e1-Busan-Daejeon'
        dir_data = '../output/dataset/{}_real_traffic.xlsx'.format(self.link)
        self.df_data = pd.read_excel(dir_data)
        self.df_data = self.df_data.drop(['date', 'link_availability'], axis=1)
        self.df_np_data = self.normalization()

    ##########################
    ## 2.Data Normalization ##
    ##########################
    def normalization(self):
        # 일반 정규화
        scaler = MinMaxScaler()
        df_data_normal = self.df_data.copy()
        df_data_normal[:] = scaler.fit_transform(df_data_normal[:])
        # df_data_normal.drop(['tx_link_utilization'], axis=1, inplace=True)
        # print(df_data_normal)
        df_np_data = df_data_normal.to_numpy()
        return df_np_data

    ###################################
    ## 3.Generate TRAIN/TEST Dataset ##
    ###################################

    # 현재 10분단위 데이터 30개를 넣고 다음 10분을 예측하는 모델을 위한 데이터셋 생성
    def generateX(self, a, n):
        x_train = []
        y_train = []
        for i in range(len(a)):
            x = a[i:(i + n)]
            if (i + n) < len(a)-1:
                x_train.append(x)          # 10분단위 1번~30번(30개)
                y_train.append(a[i + n])   # 31번(=다음 10분)
            else:
                break
        return np.array(x_train), np.array(y_train)

    def gen_ai_model(self):

        x, y = self.generateX(self.df_np_data, 30)
        print(x.shape)
        print(y.shape)

        # 학습용 데이터와 시험용 데이터 → (8:2)로 분할
        X_train = x[:int(x.shape[0]*0.8),:, :]
        Y_train = y[:int(y.shape[0]*0.8),:]
        X_test = x[int(x.shape[0]*0.8):,:,:]
        Y_test = y[int(y.shape[0]*0.8):,:]

        # Train 및 Test 데이터셋
        print(X_train.shape)
        print(Y_train.shape)
        print(X_test.shape)
        print(Y_test.shape)


        # Model 구성
        layers = [X_train.shape[1], X_train.shape[2], 1] # (30, 5, 1) = (10분단위 30개 데이터, 벡터5개, 1)
        model = Sequential()
        model.add(Bidirectional(LSTM(layers[0],
                                input_shape=(layers[0], layers[1]),
                                return_sequences=True)))
        model.add(Dropout(0.2))
        model.add(LSTM(layers[0],
                       return_sequences=True))
        model.add(Dropout(0.2))
        model.add(LSTM(layers[0]))
        model.add(Dropout(0.2))
        model.add(Dense(layers[1],
                        activation='linear')) # Model Output → 5x1(5개의 벡터를 예측)

        # model = multi_gpu_model(model, gpus=2)
        model.compile(loss="mse",
                      optimizer="adam",
                      metrics=['accuracy'])

        model.fit(X_train,  # datas
                  Y_train,  # labels
                  batch_size=100,
                  epochs=100,
                  validation_split=0.05)
        model.summary()

        model.save('./output/model/Bi-LSTM_N30_L3_V5_model_{}.h5'.format(self.link))
