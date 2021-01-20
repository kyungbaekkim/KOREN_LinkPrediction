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
    # 10�п� �ѹ��� web(FileSystem)���� Traffice�� ����
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
    # ���� ������ Traffice�� �ִٸ� Prediction ����(����ð��� �������� 10�� 30�� 1�ð� ���� ����)
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
    # 10�п� �ѹ��� web(FileSystem)���� Traffice�� ����
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
    # �͹̳ηκ��� �����ϰ���� ��ũ�������̽��� ����ɼ��� ���޹���
    # ��ũ �������̽� ���� ==> P2-Daejeon-prs1e11-Daejeon-Gwangju
    # �ɼ� ���� ==> 0:�ǽð� ���� 1: �ʱ�ȭ(�ϰ�ó��) ����
    p = argparse.ArgumentParser()

    # python MainApp.py -link P2-Daejeon-prs1e11-Daejeon-Gwangju -init 1 ==> �ʱ�ȭ ����(���ź��� ������� ��� ����)
    # python MainApp.py -link P2-Daejeon-prs1e11-Daejeon-Gwangju -init 0 ==> �ǽð� ����(����ð����� 10�д��� �ǽð� ����)
    p.add_argument("-link", "--LINK_PATH", default="P2-Daejeon-prs1e11-Daejeon-Gwangju") # ���� �� ���� �� Link�� �޴´� ex) ����-����
    p.add_argument("-init", "--INIT_PATH", default="0")  # ���� �� ���� �� Link�� �޴´� ex) ����-����
    args = p.parse_args()

    ##########################
    ## 2.Scheduling Program ##
    ##########################
    # 10�п� �ѹ��� FileSystem���� Traffic ����
    if args.INIT_PATH == '1': # Batch Process
        # ���ź��� ������� �ش� ��ũ�������̽��� ��Ʈ��ũ���������� �����ϰ� MongoDB�� ����
        # AI���� ���� ���� 10��, 30��, 60������ ��Ʈ��ũ���������� �����ϰ� ElasticSearch�� ����
        print('[RUNNING] INIT Program Start')
        init_job(args)
    else: # Real-Time Process
        # �ش� ��ũ�������̽����� 10�д����� �����Ǵ� ��Ʈ��ũ ���������� �ǽð����� �����Ͽ� MongoDB�� ����
        # AI���� ���� ���� 10��, 30��, 60������ ��Ʈ��ũ���������� �����ϰ� ElasticSearch�� ����
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