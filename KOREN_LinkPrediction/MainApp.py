# -*- coding: euc-kr -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
import argparse
import datetime
from openpyxl import load_workbook
from openpyxl import workbook
from apscheduler.schedulers.background import BackgroundScheduler
from collector.RealtimeTrafficCollector import RealtimeTrafficCollector
from collector.TrafficCollector import TrafficCollector
from LSTM_model.RealtimeRecursiveEvalModel import RealtimeRecursiveEvalModel
from LSTM_model.KORENModel10Min import GenAI10Min


def realtime_job(args):
    #####################################
    ## 3.Traffic Collection(Real-Time) ##
    #####################################
    # 10분에 한번씩 web(FileSystem)에서 Traffice을 수집
    try:
        now = datetime.datetime.now()
        print('[RUNNING]: Program Execute >> [TIME]: {}'.format(now))

        collector = RealtimeTrafficCollector(args.LINK_PATH)
        flag, new_cnt = collector.realtime_crawler()
    except Exception as e:
        print('[ERROR]: Collector does not work.')
        exit()

    #####################################
    ## 4.Traffic Prediction(Real-Time) ##
    #####################################
    # 새로 수집된 Traffice이 있다면 Prediction 진행(현재시간을 기준으로 10분 30분 1시간 각각 예측)
    try:
        if flag == 1:
            print('[RUNNING]: Traffic Prediction >> [TIME]: {}'.format(now))
            predictor = RealtimeRecursiveEvalModel(args.LINK_PATH, new_cnt, flag=0)
            predictor.predictions_model()
    except Exception as e:
        print(e)

def init_job(args):
    #################################
    ## 3.Traffic Collection(Batch) ##
    #################################
    # 10분에 한번씩 web(FileSystem)에서 Traffice을 수집
    now = datetime.datetime.now()
    print('[RUNNING]: Program Execute >> [TIME]: {}'.format(now))

    collector = TrafficCollector(args.LINK_PATH)
    new_cnt = collector.web_crawler()

    ################################
    ## 4.Generate AI Model(Train) ##
    ################################
    genAI = GenAI10Min(args.LINK_PATH)
    genAI.gen_ai_model()

    #################################
    ## 5.Traffic Prediction(Batch) ##
    #################################
    print('[RUNNING]: Traffic Prediction >> [TIME]: {}'.format(now))
    predictor = RealtimeRecursiveEvalModel(args.LINK_PATH, new_cnt, flag=1)
    predictor.predictions_model()


def main():
    ##########################
    ## 1.Receiving Argument ##
    ##########################\
    # 터미널로부터 예측하고싶은 링크인터페이스와 실행옵션을 전달받음
    # 링크 인터페이스 예시 ==> P2-Daejeon-prs1e11-Daejeon-Gwangju
    # 옵션 예시 ==> 0:실시간 동작 1: 초기화(일괄처리) 동작
    p = argparse.ArgumentParser()

    # python MainApp.py -link P2-Daejeon-prs1e11-Daejeon-Gwangju -init 1 ==> 초기화 진행(과거부터 현재까지 결과 저장)
    # python MainApp.py -link P2-Daejeon-prs1e11-Daejeon-Gwangju -init 0 ==> 실시간 실행(현재시간부터 10분단위 실시간 저장)
    p.add_argument("-link", "--LINK_PATH", default="P2-Daejeon-prs1e11-Daejeon-Gwangju") # 수집 및 예측 할 Link를 받는다 ex) 대전-광주
    p.add_argument("-init", "--INIT_PATH", default="0")  # 수집 및 예측 할 Link를 받는다 ex) 대전-광주
    args = p.parse_args()

    ##########################
    ## 2.Scheduling Program ##
    ##########################
    # 10분에 한번씩 FileSystem에서 Traffic 수집
    if args.INIT_PATH == '1': # Batch Process
        # 과거부터 현재까지 해당 링크인터페이스의 네트워크상태정보를 수집하고 MongoDB에 저장
        # AI모델을 통해 다음 10분, 30분, 60분후의 네트워크상태정보를 예측하고 ElasticSearch에 저장
        print('[RUNNING] INIT Program Start')
        init_job(args)
    else: # Real-Time Process
        # 해당 링크인터페이스에서 10분단위로 생성되는 네트워크 상태정보를 실시간으로 수집하여 MongoDB에 저장
        # AI모델을 통해 다음 10분, 30분, 60분후의 네트워크상태정보를 예측하고 ElasticSearch에 저장
        print('[RUNNING] Real-Time Program Start')
        sched = BackgroundScheduler()
        sched.start()
        sched.add_job(realtime_job, 'cron', minute='*/20', kwargs={'args': args})

        now = datetime.datetime.now()
        while True:
            print('[RUNNING]: Running Main Process >> [TIME]: {}'.format(now))
            time.sleep(30)


#####################
## 0.Program Start ##
#####################
if __name__ == '__main__':
    main()