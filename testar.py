
import psycopg2
from pymongo import MongoClient

# Testar conexão com PostgreSQL
try:
    conexao_pg = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="biblioteca",
        user="postgres",
        password="P@t06188"
    )

    print("PostgreSQL conectado com sucesso!")

    conexao_pg.close()

except Exception as erro:
    print("Erro ao conectar ao PostgreSQL:", erro)


# Testar conexão com MongoDB
try:
    cliente_mongo = MongoClient(
        "mongodb://localhost:27017/",
        serverSelectionTimeoutMS=5000
    )

    cliente_mongo.admin.command("ping")

    print("MongoDB conectado com sucesso!")

    cliente_mongo.close()

except Exception as erro:
    print("Erro ao conectar ao MongoDB:", erro)
