import sqlite3
import os
import json
from datetime import datetime

DB_FILE = "zapfinder.db"

def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabela de Histórico de Envios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS envio_historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_envio TEXT,
        produto_titulo TEXT,
        canal_envio TEXT,
        status TEXT
    )
    """)
    
    # Tabela de Agendamentos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        horario TEXT,
        ativo INTEGER,
        config TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def salvar_historico(produto, canal, status):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO envio_historico (data_envio, produto_titulo, canal_envio, status) VALUES (?, ?, ?, ?)",
                       (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), produto, canal, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar historico: {e}")

def ler_historico(limit=50):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, data_envio, produto_titulo, status FROM envio_historico ORDER BY id DESC LIMIT ?", (limit,))
        dados = cursor.fetchall()
        conn.close()
        return dados
    except Exception as e:
        print(f"Erro ao ler historico: {e}")
        return []

def obter_produtos_enviados_sucesso(limit=1000):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT produto_titulo FROM envio_historico WHERE status = 'Sucesso' ORDER BY id DESC LIMIT ?", (limit,))
        dados = [row[0] for row in cursor.fetchall()]
        conn.close()
        return set(dados)
    except Exception as e:
        print(f"Erro ao obter produtos enviados: {e}")
        return set()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")

