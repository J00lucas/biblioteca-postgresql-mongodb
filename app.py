import psycopg2
from pymongo import MongoClient
from datetime import datetime, timezone


# ==========================================
# 1. CONEXÃO COM O POSTGRESQL LOCAL
# ==========================================

def conectar_postgresql():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="biblioteca",
        user="postgres",
        password="SUA_SENHA"
    )


# ==========================================
# 2. CONEXÃO COM O MONGODB
# ==========================================

mongo_client = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

# Verifica se o MongoDB está acessível.
mongo_client.admin.command("ping")

mongo_db = mongo_client["biblioteca_logs"]
colecao_eventos = mongo_db["eventos_sistema"]


# ==========================================
# 3. REGISTRO DE EVENTOS DE AUDITORIA
# ==========================================

def registrar_evento_nosql(
    tipo_evento,
    detalhes,
    id_usuario=None,
    id_livro=None
):
    evento = {
        "tipo_evento": tipo_evento,
        "detalhes": detalhes,
        "id_usuario": id_usuario,
        "id_livro": id_livro,
        "data_evento": datetime.now(timezone.utc)
    }

    colecao_eventos.insert_one(evento)

    print(f"Evento registrado no MongoDB: {tipo_evento}")


# ==========================================
# 4. REALIZAÇÃO DO EMPRÉSTIMO
# ==========================================

def emprestar_livro(id_usuario, id_livro):

    conexao = None

    try:
        # Conecta ao PostgreSQL local.
        conexao = conectar_postgresql()

        # Utiliza uma transação no banco relacional.
        with conexao:
            with conexao.cursor() as cursor:

                # ----------------------------------
                # Verifica e atualiza o estoque.
                # ----------------------------------

                cursor.execute(
                    """
                    UPDATE public.livro
                    SET quantidade_disponivel =
                        quantidade_disponivel - 1
                    WHERE id_livro = %s
                      AND quantidade_disponivel > 0
                    RETURNING id_livro;
                    """,
                    (id_livro,)
                )

                livro_atualizado = cursor.fetchone()

                if livro_atualizado is None:
                    raise ValueError(
                        "Livro inexistente ou sem exemplares disponíveis."
                    )

                # ----------------------------------
                # Cria o empréstimo.
                # Devolução prevista em 14 dias.
                # ----------------------------------

                cursor.execute(
                    """
                    INSERT INTO public.emprestimo (
                        id_usuario,
                        data_devolucao_prevista
                    )
                    VALUES (
                        %s,
                        NOW() + INTERVAL '14 days'
                    )
                    RETURNING id_emprestimo;
                    """,
                    (id_usuario,)
                )

                id_emprestimo = cursor.fetchone()[0]

                # ----------------------------------
                # Relaciona o empréstimo ao livro.
                # ----------------------------------

                cursor.execute(
                    """
                    INSERT INTO public.item_emprestimo (
                        id_emprestimo,
                        id_livro
                    )
                    VALUES (%s, %s);
                    """,
                    (id_emprestimo, id_livro)
                )

        # O bloco with confirma a transação
        # quando todas as operações dão certo.

        print("Empréstimo realizado com sucesso!")
        print(f"ID do empréstimo: {id_emprestimo}")

        # ----------------------------------
        # Registra o sucesso no MongoDB.
        # ----------------------------------

        try:
            registrar_evento_nosql(
                tipo_evento="EMPRESTIMO_SUCESSO",
                detalhes=(
                    f"Empréstimo {id_emprestimo} "
                    f"realizado com sucesso."
                ),
                id_usuario=id_usuario,
                id_livro=id_livro
            )

        except Exception as erro_log:
            print(
                "Aviso: empréstimo confirmado no PostgreSQL, "
                "mas não foi possível registrar a auditoria "
                f"no MongoDB: {erro_log}"
            )

        return id_emprestimo

    except Exception as erro:

        # Se houver uma falha durante a transação,
        # desfaz as alterações pendentes.

        if conexao is not None:
            conexao.rollback()

        print(f"Erro ao realizar empréstimo: {erro}")

        # Registra a falha no MongoDB.
        try:
            registrar_evento_nosql(
                tipo_evento="EMPRESTIMO_FALHA",
                detalhes=str(erro),
                id_usuario=id_usuario,
                id_livro=id_livro
            )

        except Exception as erro_log:
            print(
                "Não foi possível registrar a falha "
                f"no MongoDB: {erro_log}"
            )

        return None

    finally:
        if conexao is not None:
            conexao.close()


# ==========================================
# 5. EXECUÇÃO DO TESTE
# ==========================================

if __name__ == "__main__":

    try:
        emprestar_livro(
            id_usuario=1,
            id_livro=2
        )

    finally:
        mongo_client.close()