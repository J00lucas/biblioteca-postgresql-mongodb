from flask import Flask, render_template, jsonify, request
import psycopg2
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

def conectar_postgresql():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="biblioteca",
        user="postgres",
        password="P@t06188"
    )

mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["biblioteca_logs"]
mongo_collection = mongo_db["eventos_sistema"]

def registrar_evento_nosql(tipo_evento, detalhes, id_usuario=None, id_livro=None):
    evento = {
        "timestamp": datetime.now(),
        "tipo_evento": tipo_evento,
        "detalhes": detalhes,
        "id_usuario": id_usuario,
        "id_livro": id_livro
    }

    mongo_collection.insert_one(evento)


@app.route("/")
def pagina_inicial():
    return render_template("index.html")


@app.route("/api/livros")
def listar_livros():
    conn = conectar_postgresql()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT
            id_livro,
            titulo,
            autor,
            isbn,
            quantidade_disponivel
        FROM public.livro
        ORDER BY id_livro;
    """)

    livros = cursor.fetchall()

    cursor.close()
    conn.close()

    resultado = []

    for livro in livros:
        resultado.append({
            "id": livro[0],
            "titulo": livro[1],
            "autor": livro[2],
            "isbn": livro[3],
            "disponivel": livro[4]
        })

    return jsonify(resultado)

@app.route("/api/usuarios")
def listar_usuarios():
    conn = conectar_postgresql()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id_usuario,
            nome,
            cpf,
            email,
            telefone
        FROM public.usuario
        ORDER BY id_usuario;
    """)

    usuarios = cursor.fetchall()

    cursor.close()
    conn.close()

    resultado = []

    for usuario in usuarios:
        resultado.append({
            "id": usuario[0],
            "nome": usuario[1],
            "cpf": usuario[2],
            "email": usuario[3],
            "telefone": usuario[4]
        })

    return jsonify(resultado)

@app.route("/api/usuarios", methods=["POST"])
def cadastrar_usuario():
    dados = request.get_json()

    nome = dados.get("nome")
    cpf = dados.get("cpf")
    email = dados.get("email")
    telefone = dados.get("telefone")

    if not nome or not email:
        return jsonify({
            "erro": "Nome e e-mail são obrigatórios."
        }), 400

    conn = conectar_postgresql()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO public.usuario
                (nome, cpf, email, telefone)
            VALUES
                (%s, %s, %s, %s)
            RETURNING id_usuario;
        """, (nome, cpf, email, telefone))

        id_usuario = cursor.fetchone()[0]

        conn.commit()

        return jsonify({
            "mensagem": "Usuário cadastrado com sucesso.",
            "id": id_usuario,
            "nome": nome,
            "cpf": cpf,
            "email": email,
            "telefone": telefone
        }), 201

    except Exception as erro:
        conn.rollback()

        return jsonify({
            "erro": str(erro)
        }), 400

    finally:
        cursor.close()
        conn.close()

@app.route("/api/emprestimos", methods=["POST"])
def realizar_emprestimo():
    dados = request.get_json()

    id_usuario = dados.get("id_usuario")
    id_livro = dados.get("id_livro")

    if not id_usuario or not id_livro:
        return jsonify({
            "erro": "Usuário e livro são obrigatórios."
        }), 400

    conn = conectar_postgresql()
    cursor = conn.cursor()

    try:
        # Verifica se o livro existe e possui estoque
        cursor.execute("""
            SELECT quantidade_disponivel
            FROM public.livro
            WHERE id_livro = %s;
        """, (id_livro,))

        livro = cursor.fetchone()

        if livro is None:
            return jsonify({
                "erro": "Livro não encontrado."
            }), 404

        quantidade_disponivel = livro[0]

        if quantidade_disponivel <= 0:
            return jsonify({
                "erro": "Livro sem estoque disponível."
            }), 400

        # Diminui o estoque
        cursor.execute("""
            UPDATE public.livro
            SET quantidade_disponivel = quantidade_disponivel - 1
            WHERE id_livro = %s;
        """, (id_livro,))

        # Cria o empréstimo
        cursor.execute("""
            INSERT INTO public.emprestimo
                (id_usuario, data_devolucao_prevista)
            VALUES
                (%s, NOW() + INTERVAL '14 days')
            RETURNING id_emprestimo;
        """, (id_usuario,))

        id_emprestimo = cursor.fetchone()[0]

        # Relaciona o livro ao empréstimo
        cursor.execute("""
            INSERT INTO public.item_emprestimo
                (id_emprestimo, id_livro)
            VALUES
                (%s, %s);
        """, (id_emprestimo, id_livro))

        conn.commit()

        registrar_evento_nosql(
            "EMPRESTIMO_SUCESSO",
            f"Empréstimo do livro ID {id_livro} realizado.",
            id_usuario,
            id_livro
        )

        return jsonify({
            "mensagem": "Empréstimo realizado com sucesso.",
            "id_emprestimo": id_emprestimo,
            "id_usuario": id_usuario,
            "id_livro": id_livro
        }), 201

    except Exception as erro:
        conn.rollback()

        return jsonify({
            "erro": str(erro)
        }), 400

    finally:
        cursor.close()
        conn.close()
    
@app.route("/api/logs")
def listar_logs():
    eventos = mongo_collection.find().sort("timestamp", -1)

    resultado = []

    for evento in eventos:

        data_evento = evento.get("timestamp") or evento.get("data_evento")

    resultado.append({
    "tipo_evento": evento.get("tipo_evento"),
    "detalhes": evento.get("detalhes"),
    "id_usuario": evento.get("id_usuario"),
    "id_livro": evento.get("id_livro"),
    "timestamp": data_evento.isoformat() if data_evento else None
})

    return jsonify(resultado)

if __name__ == "__main__":
    app.run(debug=True)