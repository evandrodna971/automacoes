import unittest
import random
from core.mercadolivre import buscar_ofertas_ml_reais

class TestCombined(unittest.TestCase):
    def test_combining_and_shuffling(self):
        # Simula ofertas da Shopee
        produtos_shopee = [
            {"titulo": "Produto Shopee 1", "preco": "50.00", "fonte": "Shopee", "link": "https://shopee.com.br/1"},
            {"titulo": "Produto Shopee 2", "preco": "75.00", "fonte": "Shopee", "link": "https://shopee.com.br/2"},
        ]
        
        # Busca ofertas reais do Mercado Livre
        produtos_ml = buscar_ofertas_ml_reais(termo="ofertas", tag_afiliado="testtag", limit=2, log_func=print)
        self.assertGreater(len(produtos_ml), 0)
        
        # Junta e embaralha
        todos = produtos_shopee + produtos_ml
        self.assertEqual(len(todos), len(produtos_shopee) + len(produtos_ml))
        
        random.shuffle(todos)
        
        fontes = [p["fonte"] for p in todos]
        print(f"[OK] Fontes obtidas no sorteio misto: {fontes}")
        self.assertIn("Shopee", fontes)
        self.assertIn("Mercado Livre", fontes)

if __name__ == "__main__":
    unittest.main()
