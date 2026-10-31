from pymongo import MongoClient

cliente = MongoClient("mongodb://localhost:27017/")

colecao = cliente["biblioteca_logs"]["eventos_sistema"]

for evento in colecao.find():
    print(evento)

cliente.close()