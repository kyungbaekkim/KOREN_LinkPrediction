

from pymongo import MongoClient



class TrafficDAO:
    reply_list = []  # MongoDB Document를 담을 List
    ##########################
    ## 1.MongoDB Connection ##
    ##########################
    def __init__(self):
        # >> MongoDB Connection
        self.client = MongoClient('localhost', 27017) # 클래스 객체 할당(ip주소, port번호)
        self.db = self.client['local']  # MongoDB의 'local' DB를 할당
        # self.collection = self.db.movie
        self.col_traffic = self.db.get_collection('traffic')  # 동적으로 Collection 선택
        self.col_actual = self.db.get_collection('real')
        self.col_prediction = self.db.get_collection('prediction')

    ######################
    ## 2.MongoDB Insert ##
    ######################
    # 2.1예측된 네트워크 상태정보를 MongoDB에 저장
    def write_predict(self, data):
        print('>> MongoDB write data!')
        self.col_prediction.insert(data) # JSON Type = Dict Type(python)

    # 2.2실제 네트워크 상태정보를 MongoDB에 저장
    def write_real(self, data):
        print('>> MongoDB write data!')
        self.col_actual.insert(data)  # JSON Type = Dict Type(python)
