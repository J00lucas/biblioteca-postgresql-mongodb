from flask import Flask, render_template, jsonify, request
import psycopg2
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

load_dotenv()

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
PASTA_BACKUPS = BASE_DIR / "backups"
PASTA_BACKUPS.mkdir(exist_ok=True)

PG_HOST = "localhost"
PG_PORT = "5432"
PG_USER = "postgres"
PG_DATABASE = "biblioteca"
PG_PASSWORD = os.getenv("DB_PASSWORD")

PG_BIN = Path(r"C:\Program Files\PostgreSQL\18\bin")
PG_DUMP = PG_BIN / "pg_dump.exe"
PG_RESTORE = PG_BIN / "pg_restore.exe"

MONGO_URI = "mongodb://localhost:27017/"
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["biblioteca_logs"]
mongo_collection = mongo_db["eventos_sistema"]


def conectar_postgresql():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD
    )


def registrar_evento_nosql(tipo_evento, detalhes, id_usuario=None, id_livro=None):
    evento = {
        "tipo_evento": tipo_evento,
        "detalhes": detalhes,
        "id_usuario": id_usuario,
        "id_livro": id_livro,
        "timestamp": datetime.now().isoformat()
    }

    print("REGISTRANDO EVENTO NO MONGODB:", evento)
    mongo_collection.insert_one(evento)


def criar_backup_postgresql(prefixo="backup"):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome_arquivo = f"{prefixo}_{timestamp}.backup"
    caminho_backup = PASTA_BACKUPS / nome_arquivo

    comando = [
        str(PG_DUMP),
        "-h", PG_HOST,
        "-p", PG_PORT,
        "-U", PG_USER,
        "-F", "c",
        "-f", str(caminho_backup),
        PG_DATABASE
    ]

    ambiente = os.environ.copy()
    ambiente["PGPASSWORD"] = PG_PASSWORD

    resultado = subprocess.run(
        comando,
        env=ambiente,
        capture_output=True,
        text=True
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            resultado.stderr.strip() or "Erro ao criar backup."
        )

    return nome_arquivo


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/backup", methods=["POST"])
def criar_backup():
    try:
        nome_arquivo = criar_backup_postgresql("backup")

        registrar_evento_nosql(
            "BACKUP_CRIADO",
            f"Backup PostgreSQL criado: {nome_arquivo}"
        )

        return jsonify({
            "mensagem": "Backup criado com sucesso.",
            "arquivo": nome_arquivo
        }), 200

    except Exception as e:
        print("Erro ao criar backup:", e)

        return jsonify({
            "erro": str(e)
        }), 500


@app.route("/api/backups", methods=["GET"])
def listar_backups():
    try:
        backups = []

        for arquivo in PASTA_BACKUPS.glob("*.backup"):
            estatisticas = arquivo.stat()

            backups.append({
                "arquivo": arquivo.name,
                "tamanho": estatisticas.st_size,
                "data": datetime.fromtimestamp(
                    estatisticas.st_mtime
                ).strftime("%d/%m/%Y %H:%M:%S")
            })

        backups.sort(
            key=lambda x: x["arquivo"],
            reverse=True
        )

        return jsonify(backups), 200

    except Exception as e:
        return jsonify({
            "erro": str(e)
        }), 500


@app.route("/api/backup/restaurar", methods=["POST"])
def restaurar_backup():
    try:
        dados = request.get_json()

        if not dados:
            return jsonify({
                "erro": "Nenhum dado foi enviado."
            }), 400

        nome_arquivo = dados.get("arquivo")

        if not nome_arquivo:
            return jsonify({
                "erro": "Nome do backup não informado."
            }), 400

        nome_arquivo = Path(nome_arquivo).name

        if not nome_arquivo.endswith(".backup"):
            return jsonify({
                "erro": "Arquivo de backup inválido."
            }), 400

        caminho_backup = PASTA_BACKUPS / nome_arquivo

        if not caminho_backup.exists():
            return jsonify({
                "erro": "Backup não encontrado."
            }), 404

        if not PG_RESTORE.exists():
            return jsonify({
                "erro": "pg_restore.exe não foi encontrado."
            }), 500

        backup_seguranca = criar_backup_postgresql(
            "backup_antes_restauracao"
        )

        comando = [
            str(PG_RESTORE),
            "-h", PG_HOST,
            "-p", PG_PORT,
            "-U", PG_USER,
            "-d", PG_DATABASE,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--exit-on-error",
            str(caminho_backup)
        ]

        ambiente = os.environ.copy()
        ambiente["PGPASSWORD"] = PG_PASSWORD

        resultado = subprocess.run(
            comando,
            env=ambiente,
            capture_output=True,
            text=True
        )

        if resultado.returncode != 0:
            return jsonify({
                "erro": "Não foi possível restaurar o backup.",
                "detalhes": resultado.stderr.strip(),
                "backup_seguranca": backup_seguranca
            }), 500

        registrar_evento_nosql(
            "BACKUP_RESTAURADO",
            (
                f"Backup restaurado: {nome_arquivo}. "
                f"Backup de segurança criado antes da restauração: "
                f"{backup_seguranca}"
            )
        )

        return jsonify({
            "mensagem": "Backup restaurado com sucesso.",
            "arquivo": nome_arquivo,
            "backup_seguranca": backup_seguranca
        }), 200

    except Exception as e:
        print("Erro ao restaurar backup:", e)

        return jsonify({
            "erro": str(e)
        }), 500


@app.route("/api/livros", methods=["GET", "POST"])
def livros():
    conexao = conectar_postgresql()
    cursor = conexao.cursor()

    try:
        if request.method == "GET":
            cursor.execute("""
                SELECT
                    id_livro,
                    titulo,
                    autor,
                    isbn,
                    quantidade_disponivel,
                    capa_url
                FROM public.livro
                ORDER BY id_livro
            """)

            resultados = cursor.fetchall()

            livros = []

            for livro in resultados:
                livros.append({
                    "id_livro": livro[0],
                    "titulo": livro[1],
                    "autor": livro[2],
                    "isbn": livro[3],
                    "quantidade_disponivel": livro[4],
                    "capa_url": livro[5]
                })

            return jsonify(livros), 200

        dados = request.get_json()

        titulo = dados.get("titulo")
        autor = dados.get("autor")
        isbn = dados.get("isbn")
        quantidade = dados.get("quantidade_disponivel", 0)
        capa_url = dados.get("capa_url")

        cursor.execute("""
            INSERT INTO public.livro
                (
                    titulo,
                    autor,
                    isbn,
                    quantidade_disponivel,
                    capa_url
                )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_livro
        """, (
            titulo,
            autor,
            isbn,
            quantidade,
            capa_url
        ))

        id_livro = cursor.fetchone()[0]

        conexao.commit()

        registrar_evento_nosql(
            "LIVRO_CADASTRADO",
            f"Livro cadastrado: {titulo}",
            id_livro=id_livro
        )

        return jsonify({
            "mensagem": "Livro cadastrado com sucesso.",
            "id_livro": id_livro
        }), 201

    except Exception as e:
        conexao.rollback()

        return jsonify({
            "erro": str(e)
        }), 400

    finally:
        cursor.close()
        conexao.close()


@app.route("/api/livros/<int:id_livro>", methods=["DELETE"])
def apagar_livro(id_livro):
    conexao = conectar_postgresql()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "SELECT titulo FROM public.livro WHERE id_livro = %s",
            (id_livro,)
        )

        livro = cursor.fetchone()

        if not livro:
            return jsonify({
                "erro": "Livro não encontrado."
            }), 404

        titulo = livro[0]

        cursor.execute(
            "DELETE FROM public.livro WHERE id_livro = %s",
            (id_livro,)
        )

        conexao.commit()

        registrar_evento_nosql(
            "LIVRO_EXCLUIDO",
            f"Livro excluído: {titulo}",
            id_livro=id_livro
        )

        return jsonify({
            "mensagem": "Livro excluído com sucesso."
        }), 200

    except Exception as e:
        conexao.rollback()

        return jsonify({
            "erro": str(e)
        }), 400

    finally:
        cursor.close()
        conexao.close()


@app.route("/api/usuarios", methods=["GET", "POST"])
def usuarios():
    conexao = conectar_postgresql()
    cursor = conexao.cursor()

    try:
        if request.method == "GET":
            cursor.execute("""
                SELECT
                    id_usuario,
                    nome,
                    cpf,
                    email,
                    telefone,
                    data_cadastro
                FROM public.usuario
                ORDER BY id_usuario
            """)

            resultados = cursor.fetchall()

            usuarios = []

            for usuario in resultados:
                usuarios.append({
                    "id_usuario": usuario[0],
                    "nome": usuario[1],
                    "cpf": usuario[2],
                    "email": usuario[3],
                    "telefone": usuario[4],
                    "data_cadastro": usuario[5]
                })

            return jsonify(usuarios), 200

        dados = request.get_json()

        nome = dados.get("nome")
        cpf = dados.get("cpf")
        email = dados.get("email")
        telefone = dados.get("telefone")

        cursor.execute("""
            INSERT INTO public.usuario
                (
                    nome,
                    cpf,
                    email,
                    telefone
                )
            VALUES (%s, %s, %s, %s)
            RETURNING id_usuario
        """, (
            nome,
            cpf,
            email,
            telefone
        ))

        id_usuario = cursor.fetchone()[0]

        conexao.commit()

        registrar_evento_nosql(
            "USUARIO_CADASTRADO",
            f"Usuário cadastrado: {nome}",
            id_usuario=id_usuario
        )

        return jsonify({
            "mensagem": "Usuário cadastrado com sucesso.",
            "id_usuario": id_usuario
        }), 201

    except Exception as e:
        conexao.rollback()

        return jsonify({
            "erro": str(e)
        }), 400

    finally:
        cursor.close()
        conexao.close()


@app.route("/api/emprestimos", methods=["POST"])
def criar_emprestimo():
    conexao = conectar_postgresql()
    cursor = conexao.cursor()

    try:
        dados = request.get_json()

        id_usuario = dados.get("id_usuario")
        id_livro = dados.get("id_livro")

        cursor.execute("""
            SELECT 1
            FROM public.emprestimo e
            JOIN public.item_emprestimo i
                ON i.id_emprestimo = e.id_emprestimo
            WHERE e.id_usuario = %s
              AND i.id_livro = %s
        """, (
            id_usuario,
            id_livro
        ))

        if cursor.fetchone():
            return jsonify({
                "erro": "Este leitor já possui este livro emprestado."
            }), 400

        cursor.execute("""
            SELECT quantidade_disponivel
            FROM public.livro
            WHERE id_livro = %s
        """, (id_livro,))

        livro = cursor.fetchone()

        if not livro:
            return jsonify({
                "erro": "Livro não encontrado."
            }), 404

        if livro[0] <= 0:
            return jsonify({
                "erro": "Livro sem estoque disponível."
            }), 400

        cursor.execute("""
            INSERT INTO public.emprestimo
                (
                    id_usuario,
                    data_devolucao_prevista
                )
            VALUES
                (
                    %s,
                    NOW() + INTERVAL '14 days'
                )
            RETURNING id_emprestimo, data_devolucao_prevista
        """, (id_usuario,))

        id_emprestimo, data_devolucao = cursor.fetchone()

        cursor.execute("""
            INSERT INTO public.item_emprestimo
                (
                    id_emprestimo,
                    id_livro
                )
            VALUES (%s, %s)
        """, (
            id_emprestimo,
            id_livro
        ))

        cursor.execute("""
            UPDATE public.livro
            SET quantidade_disponivel =
                quantidade_disponivel - 1
            WHERE id_livro = %s
        """, (id_livro,))

        conexao.commit()

        registrar_evento_nosql(
            "EMPRESTIMO_SUCESSO",
            f"Empréstimo realizado. ID do empréstimo: {id_emprestimo}",
            id_usuario=id_usuario,
            id_livro=id_livro
        )

        return jsonify({
            "mensagem": "Empréstimo realizado com sucesso.",
            "id_emprestimo": id_emprestimo,
            "devolucao_prevista": data_devolucao.strftime(
                "%d/%m/%Y"
            )
        }), 201

    except Exception as e:
        conexao.rollback()

        return jsonify({
            "erro": str(e)
        }), 400

    finally:
        cursor.close()
        conexao.close()


@app.route("/api/emprestimos/usuario/<int:id_usuario>", methods=["GET"])
def emprestimos_usuario(id_usuario):
    conexao = conectar_postgresql()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT
                e.id_emprestimo,
                i.id_livro,
                l.titulo,
                e.data_devolucao_prevista
            FROM public.emprestimo e
            JOIN public.item_emprestimo i
                ON i.id_emprestimo = e.id_emprestimo
            JOIN public.livro l
                ON l.id_livro = i.id_livro
            WHERE e.id_usuario = %s
            ORDER BY e.data_emprestimo DESC
        """, (id_usuario,))

        resultados = cursor.fetchall()

        emprestimos = []

        for item in resultados:
            emprestimos.append({
                "id_emprestimo": item[0],
                "id_livro": item[1],
                "titulo": item[2],
                "data_prevista": item[3].strftime("%d/%m/%Y")
            })

        return jsonify(emprestimos), 200

    except Exception as e:
        return jsonify({
            "erro": str(e)
        }), 500

    finally:
        cursor.close()
        conexao.close()


@app.route("/api/devolucoes", methods=["POST"])
def devolver_livro():
    conexao = conectar_postgresql()
    cursor = conexao.cursor()

    try:
        dados = request.get_json()

        id_usuario = dados.get("id_usuario")
        id_livro = dados.get("id_livro")
        id_emprestimo = dados.get("id_emprestimo")

        if not id_emprestimo:
            cursor.execute("""
                SELECT e.id_emprestimo
                FROM public.emprestimo e
                JOIN public.item_emprestimo i
                    ON i.id_emprestimo = e.id_emprestimo
                WHERE e.id_usuario = %s
                  AND i.id_livro = %s
                LIMIT 1
            """, (
                id_usuario,
                id_livro
            ))

            resultado = cursor.fetchone()

            if not resultado:
                return jsonify({
                    "erro": "Empréstimo não encontrado."
                }), 404

            id_emprestimo = resultado[0]

        cursor.execute("""
            DELETE FROM public.item_emprestimo
            WHERE id_emprestimo = %s
              AND id_livro = %s
        """, (
            id_emprestimo,
            id_livro
        ))

        if cursor.rowcount == 0:
            return jsonify({
                "erro": "Livro não encontrado neste empréstimo."
            }), 404

        cursor.execute("""
            UPDATE public.livro
            SET quantidade_disponivel =
                quantidade_disponivel + 1
            WHERE id_livro = %s
        """, (id_livro,))

        cursor.execute("""
            DELETE FROM public.emprestimo
            WHERE id_emprestimo = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM public.item_emprestimo
                  WHERE id_emprestimo = %s
              )
        """, (
            id_emprestimo,
            id_emprestimo
        ))

        conexao.commit()

        registrar_evento_nosql(
            "DEVOLUCAO_SUCESSO",
            f"Devolução realizada. ID do empréstimo: {id_emprestimo}",
            id_usuario=id_usuario,
            id_livro=id_livro
        )

        return jsonify({
            "mensagem": "Devolução realizada com sucesso."
        }), 200

    except Exception as e:
        conexao.rollback()

        return jsonify({
            "erro": str(e)
        }), 400

    finally:
        cursor.close()
        conexao.close()


@app.route("/api/logs", methods=["GET"])
def listar_logs():
    try:
        eventos = list(
            mongo_collection.find(
                {},
                {"_id": 0}
            ).sort("timestamp", -1)
        )

        return jsonify(eventos), 200

    except Exception as e:
        return jsonify({
            "erro": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)