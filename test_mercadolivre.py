import unittest
from core.mercadolivre import buscar_ofertas_ml_reais

class TestMercadoLivre(unittest.TestCase):
    def test_buscar_ofertas_ml_reais(self):
        produtos = buscar_ofertas_ml_reais(termo="ofertas", tag_afiliado="test12345", limit=3, log_func=print)
        self.assertIsInstance(produtos, list)
        self.assertGreater(len(produtos), 0)
        
        prod = produtos[0]
        self.assertEqual(prod["fonte"], "Mercado Livre")
        self.assertIn("titulo", prod)
        self.assertIn("preco", prod)
        self.assertIn("link", prod)
        self.assertIn("matt_tool=test12345", prod["link"])
        print("[OK] Teste Mercado Livre concluido com sucesso!")

if __name__ == "__main__":
    unittest.main()
