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
    
    # Tabela de Cupons
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        marketplace TEXT,
        title TEXT,
        discount_text TEXT,
        min_value REAL DEFAULT 0.0,
        category_tags TEXT,
        link TEXT,
        expires_at TEXT,
        created_at TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def salvar_cupons(lista_cupons):
    """Salva ou atualiza uma lista de cupons no banco de dados"""
    if not lista_cupons:
        return 0
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        inseridos = 0
        for c in lista_cupons:
            code = c.get("code", "").strip()
            marketplace = c.get("marketplace", "").strip()
            title = c.get("title", "").strip()
            discount_text = c.get("discount_text", "").strip()
            min_value = float(c.get("min_value", 0.0))
            category_tags = c.get("category_tags", "geral").strip().lower()
            link = c.get("link", "").strip()
            expires_at = c.get("expires_at", "")

            # Evita duplicidade exata do mesmo código/título e marketplace
            cursor.execute("""
                SELECT id FROM coupons 
                WHERE (code = ? AND code != '') OR (title = ? AND marketplace = ?)
            """, (code, title, marketplace))
            row = cursor.fetchone()

            if row:
                cursor.execute("""
                    UPDATE coupons 
                    SET title=?, discount_text=?, min_value=?, category_tags=?, link=?, expires_at=?, created_at=?
                    WHERE id=?
                """, (title, discount_text, min_value, category_tags, link, expires_at, agora, row[0]))
            else:
                cursor.execute("""
                    INSERT INTO coupons (code, marketplace, title, discount_text, min_value, category_tags, link, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (code, marketplace, title, discount_text, min_value, category_tags, link, expires_at, agora))
            inseridos += 1

        conn.commit()
        conn.close()
        return inseridos
    except Exception as e:
        print(f"Erro ao salvar cupons: {e}")
        return 0

def obter_cupons_validos(marketplace=None):
    """Retorna cupons ativos que ainda não expiraram"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        query = """
            SELECT id, code, marketplace, title, discount_text, min_value, category_tags, link, expires_at, created_at
            FROM coupons
            WHERE (expires_at IS NULL OR expires_at = '' OR expires_at >= ?)
        """
        params = [agora]

        if marketplace:
            query += " AND marketplace = ?"
            params.append(marketplace)

        query += " ORDER BY id DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()

        cupons = []
        for r in rows:
            cupons.append({
                "id": r[0],
                "code": r[1],
                "marketplace": r[2],
                "title": r[3],
                "discount_text": r[4],
                "min_value": r[5],
                "category_tags": r[6],
                "link": r[7],
                "expires_at": r[8],
                "created_at": r[9]
            })
        return cupons
    except Exception as e:
        print(f"Erro ao obter cupons válidos: {e}")
        return []

def limpar_cupons_expirados():
    """Remove cupons cuja data de validade já expirou"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM coupons WHERE expires_at != '' AND expires_at < ?", (agora,))
        removidos = cursor.rowcount
        conn.commit()
        conn.close()
        return removidos
    except Exception as e:
        print(f"Erro ao limpar cupons expirados: {e}")
        return 0

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


