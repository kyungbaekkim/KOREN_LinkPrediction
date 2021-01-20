# :books:Bi-LSTM기반 실시간 Link 예측 모델(KOREN_LinkPrediction)

KOREN망의 각 Link별 현재 상태를 바탕으로 향후 10분, 30분, 60분 후의 Link 상태를 예측하는 Bi-LSTM기반 인공지능 모델


## :heavy_check_mark:Developer Environment

  - Language: [:crocodile:Python 3.7](https://www.python.org/)
  - IDE Tool: [:zap:Pycharm](https://www.jetbrains.com/pycharm/)
  - Package Manager: [:snake:Anaconda](https://www.anaconda.com/)
  - AI Library: Tensorflow2, KERAS
  - Collector: Beautifulsoup4
  - Storage: MongoDB, ElasticSearch
  - Visualization: Kibana

## :book:Model Process
### 1.데이터 수집
Beautifulsoup4라이브러리를 활용하여 KOREN망의 Link정보를 수집한다.
  - timestamp
  - current_tx_packetpersecond
  - current_tx_bitpersecond
  - accumulated_tx_bytes
  - accumulated_tx_packets

### 2.데이터 전처리
수집된 Link정보를 전처리한다.
  - timestamp => (hour x 60) + Minute = time_index
  - accumulated_tx_bytes => 현재 - 10분전 = 10분동안 송신 된 bytes(tx_bytes)
  - current_tx_bitpersecond => 평균 = 10분 동안 송신된 bps 평균(tx_bitpersecond)
  - accumulated_tx_packetpersecond => 현재 - 10분전 = 10분동안 송신 된 pps 평균(tx_packetpersecond)
  - tx_link_utilization => 1 - tx_link_utilization = Link 가용량(link_availability)
  
전처리 후 생성되는 데이터
  - time_index
  - tx_bytes
  - tx_bitpersecond
  - tx_packetpersecond
  - link_availability
  
### 3.데이터 저장
전처리 된 데이터를 MongoDB에 저장한다.

### 4.Link 예측
  - 인공지능 모델: Bi-LSTM기반 다음 10분 후 Link 상태를 예측하는 모델
  - 입력 데이터: 현재를 기준으로 이전 10분단위 30개 데이터(총 300분)
  - 출력 데이터: 다음 10분 후의 Link 상태

다음 10분을 예측할 수 있는 인공지능 모델을 재귀적으로 사용하여 다음 그림과 같이 Multi-step Prediction 한다.


#### 5.시각화
