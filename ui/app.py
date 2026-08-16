import flet as ft
from database.db import init_db, salvar_historico, ler_historico, obter_produtos_enviados_sucesso, obter_cupons_validos
import threading
import time
import os
import random
from core.shopee import buscar_ofertas_shopee_reais
from core.mercadolivre import buscar_ofertas_ml_reais
from core.whatsapp import WhatsAppBot
from core.utils import baixar_imagem, copy_image_to_clipboard, formatar_mensagem_produto
from core.coupons import SmartCouponMatcher, sincronizar_todos_os_cupons

def main_app(page: ft.Page):
    page.title = "ZapFinder Automation v1.2"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_maximized = True
    page.padding = 20
    
    # Initialize DB (in thread to not block UI)
    threading.Thread(target=init_db).start()


    # --- UI COMPONENTS ---
    
    # Logs Area
    log_text = ft.Text("System ready...", color="green")
    log_column = ft.Column([log_text], scroll=ft.ScrollMode.ALWAYS, expand=True)
    log_container = ft.Container(
        content=log_column,
        border=ft.border.all(1, "grey"),
        border_radius=10,
        padding=10,
        height=200,
        bgcolor="#1F000000"
    )

    def add_log(msg):
        log_column.controls.append(ft.Text(f"> {msg}", font_family="Consolas"))
        page.update()
        
    # Refs for buttons to update state
    btn_iniciar = ft.ElevatedButton("Iniciar Envio (Shopee + Mercado Livre)")
    btn_stop = ft.ElevatedButton("Parar", icon="stop", color="red", disabled=True)
    btn_iniciar_ref = ft.Ref[ft.ElevatedButton]()
    btn_stop_ref = ft.Ref[ft.ElevatedButton]()

    # Status Indicators
    txt_enviados = ft.Text("0", size=40, weight=ft.FontWeight.BOLD)
    txt_cupons = ft.Text("0", size=40, weight=ft.FontWeight.BOLD, color="orange")
    txt_status = ft.Text("Parado", size=40, weight=ft.FontWeight.BOLD, color="red")

    # Inputs
    input_appid = ft.TextField(label="Shopee App ID", password=True, can_reveal_password=True)
    input_secret = ft.TextField(label="Shopee Secret Key", password=True, can_reveal_password=True)
    input_tag_ml = ft.TextField(label="ML matt_tool (ex: 38835395)")
    input_word_ml = ft.TextField(label="ML matt_word / Perfil (ex: joicemagalhes)")
    input_categoria = ft.Dropdown(
        label="🎯 Nicho / Categoria de Busca (Shopee + ML)",
        value="ofertas",
        options=[
            ft.dropdown.Option("ofertas", "🔥 Ofertas Gerais (Todas as Categorias)"),
            ft.dropdown.Option("moda", "👗 Moda, Roupas & Calçados"),
            ft.dropdown.Option("celular", "📱 Celulares & Smartphones"),
            ft.dropdown.Option("tecnologia", "💻 Tecnologia, Informática & TVs"),
            ft.dropdown.Option("casa", "🏠 Casa, Decoração & Cozinha"),
            ft.dropdown.Option("beleza", "💄 Beleza, Perfumes & Cuidados"),
            ft.dropdown.Option("games", "⚡ Games & Consoles"),
            ft.dropdown.Option("esporte", "⚽ Esportes, Fitness & Suplementos"),
            ft.dropdown.Option("ferramentas", "🛠️ Ferramentas & Automotivo"),
        ]
    )
    input_gemini_key = ft.TextField(label="🔑 Google Gemini API Key (Engajamento / Mensagens Especiais)", password=True, can_reveal_password=True)
    input_custom_msg = ft.TextField(
        label="✍️ Mensagem Personalizada / Tema (Salvo automaticamente)",
        multiline=True,
        min_lines=2,
        max_lines=3,
        expand=True,
        hint_text="Ex: Bom dia pessoal! Fiquem de olho nas super ofertas de hoje no grupo..."
    )
    input_grupo = ft.TextField(label="Nome do Grupo WhatsApp", value="Teste")
    input_limit = ft.TextField(label="Quantidade de Produtos (por plataforma)", value="5", keyboard_type=ft.KeyboardType.NUMBER)

    # History Data Table
    history_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Data")),
            ft.DataColumn(ft.Text("Produto")),
            ft.DataColumn(ft.Text("Status")),
        ],
        rows=[]
    )

    def load_history():
        history_table.rows.clear()
        dados = ler_historico()
        for row in dados:
            history_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(row[0]))),
                    ft.DataCell(ft.Text(str(row[1]))),
                    ft.DataCell(ft.Text(str(row[2])[:30] + "...")),
                    ft.DataCell(ft.Text(str(row[3]))),
                ])
            )
        page.update()

    # Coupons Data Table & Visual Cards
    coupons_table = ft.DataTable(
        border=ft.border.all(1, "#37474F"),
        border_radius=8,
        heading_row_color="#263238",
        columns=[
            ft.DataColumn(ft.Text("Marketplace", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Cupom / Código", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Desconto", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Mínimo", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Categoria", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Validade", weight=ft.FontWeight.BOLD)),
        ],
        rows=[]
    )

    grid_coupons_cards = ft.GridView(
        max_extent=320,
        child_aspect_ratio=2.2,
        spacing=10,
        run_spacing=10
    )

    def load_coupons():
        coupons_table.rows.clear()
        grid_coupons_cards.controls.clear()
        cupons = obter_cupons_validos()
        txt_cupons.value = str(len(cupons))
        
        for c in cupons:
            min_txt = f"R$ {c['min_value']:.2f}" if c.get('min_value', 0) > 0 else "Sem mín."
            val_txt = c.get('expires_at') or "Hoje / Indeterminado"
            mkt = c.get('marketplace', 'Geral')
            code = c.get('code', 'OFERTA')
            desc = c.get('discount_text') or c.get('title', 'Desconto Especial')
            cat = c.get('category_tags', 'Geral')

            is_shopee = "Shopee" in mkt
            card_border_color = "#FF5722" if is_shopee else "#FBC02D"
            badge_bg = "#D84315" if is_shopee else "#F57F17"

            # 1. Adiciona na DataTable
            coupons_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(mkt, weight=ft.FontWeight.BOLD, color="orange" if is_shopee else "yellow")),
                    ft.DataCell(ft.Text(code, weight=ft.FontWeight.BOLD, color="amber")),
                    ft.DataCell(ft.Text(desc[:30])),
                    ft.DataCell(ft.Text(min_txt)),
                    ft.DataCell(ft.Text(cat.upper())),
                    ft.DataCell(ft.Text(val_txt)),
                ])
            )

            # 2. Adiciona no Grid de Cards Visuais
            grid_coupons_cards.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(mkt, size=11, weight=ft.FontWeight.BOLD, color="white"),
                                bgcolor=badge_bg,
                                border_radius=4,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2)
                            ),
                            ft.Text(f"🏷️ {code}", size=14, weight=ft.FontWeight.BOLD, color="amber"),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(desc[:45], size=12, weight=ft.FontWeight.BOLD, color="white"),
                        ft.Row([
                            ft.Text(f"Mín: {min_txt}", size=11, color="white70"),
                            ft.Text(f"Val: {val_txt[:10]}", size=11, color="white70"),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ], spacing=4, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10,
                    border_radius=8,
                    bgcolor="#1E2A38",
                    border=ft.border.all(1, card_border_color)
                )
            )
        page.update()

    def on_click_sync_cupons(e=None):
        def _sync_worker():
            add_log("🔄 Buscando cupons atuais nas plataformas...")
            sincronizar_todos_os_cupons(
                appid=input_appid.value,
                secret=input_secret.value,
                tag_ml=input_tag_ml.value,
                matt_word=input_word_ml.value,
                log_func=add_log
            )
            load_coupons()
            add_log("✅ Lista de cupons atualizada com sucesso!")
        threading.Thread(target=_sync_worker, daemon=True).start()

    # --- AUTOMATION LOGIC ---
    def run_shopee_process():
        appid = input_appid.value
        secret = input_secret.value
        grupo = input_grupo.value
        tag_ml = input_tag_ml.value
        word_ml = input_word_ml.value
        categoria = input_categoria.value
        try:
            limit = int(input_limit.value)
        except:
            limit = 5

        page.process_running = True
        btn_stop.disabled = False
        btn_iniciar.disabled = True

        txt_status.value = "Rodando"
        txt_status.color = "green"
        page.update()

        try:
            # 0. Sincronização inicial de cupons se necessário
            cupons_ativos = obter_cupons_validos()
            if not cupons_ativos:
                add_log("Base de cupons vazia. Sincronizando cupons antes do envio...")
                cupons_ativos = sincronizar_todos_os_cupons(
                    appid=appid,
                    secret=secret,
                    tag_ml=tag_ml,
                    matt_word=word_ml,
                    log_func=add_log
                )
                load_coupons()

            enviados = obter_produtos_enviados_sucesso()
            produtos_shopee = []
            produtos_ml = []

            # 1. Busca ofertas da Shopee filtradas pelo nicho (se credenciais preenchidas)
            if appid and secret:
                add_log(f"Buscando ofertas na Shopee (Nicho: '{categoria}')...")
                produtos_shopee = buscar_ofertas_shopee_reais(appid, secret, termo=categoria, limit=limit, ignore_list=enviados, log_func=add_log)
            else:
                add_log("Credenciais Shopee não fornecidas. Pulando busca Shopee...")

            # 2. Busca ofertas do Mercado Livre filtradas pelo nicho
            add_log(f"Buscando ofertas no Mercado Livre (Nicho: '{categoria}')...")
            produtos_ml = buscar_ofertas_ml_reais(termo=categoria, tag_afiliado=tag_ml, matt_word=word_ml, limit=limit, ignore_list=enviados, log_func=add_log)

            # 3. Combina e embaralha produtos aleatoriamente
            produtos = produtos_shopee + produtos_ml
            random.shuffle(produtos)

            if not produtos:
                add_log("Nenhum produto encontrado nas plataformas.")
                txt_status.value = "Parado"
                txt_status.color = "red"
                page.process_running = False
                btn_stop.disabled = True
                btn_iniciar.disabled = False
                page.update()
                return

            add_log(f"Total: {len(produtos)} ofertas obtidas ({len(produtos_shopee)} Shopee + {len(produtos_ml)} Mercado Livre). Iniciando WhatsApp...")

            # 4. Iniciar WhatsApp
            bot = WhatsAppBot()
            if not bot.iniciar_driver():
                add_log("Erro ao iniciar driver do WhatsApp.")
                return

            if not bot.aguardar_login():
                add_log("Timeout no login do WhatsApp.")
                bot.fechar()
                return

            if not bot.buscar_grupo(grupo):
                add_log(f"Grupo '{grupo}' não encontrado.")
                bot.fechar()
                return

            # 5. Enviar Produtos com Validação e Matching de Cupons
            enviados_count = 0
            for i, p in enumerate(produtos):
                # Check for stop signal
                if not getattr(page, "process_running", True):
                    add_log("Processo interrompido pelo usuário.")
                    break

                fonte = p.get('fonte', 'Shopee')
                add_log(f"Enviando {i+1}/{len(produtos)} [{fonte}]: {p['titulo'][:25]}...")
                
                # Validação e Matching de Cupom Estrito
                cupom_aplicado = SmartCouponMatcher.match(p, cupons_ativos)
                if cupom_aplicado:
                    desc_tag = cupom_aplicado.get('discount_text') or cupom_aplicado.get('title')
                    add_log(f"   🏷️ Cupom associado: {desc_tag}")

                # Baixar imagem
                img_path = os.path.abspath(f"temp_prod_{i}.jpg")
                if p.get('imagem_url'):
                    baixar_imagem(p['imagem_url'], img_path)
                
                # Formatar mensagem com template nativo perfeito (preço e cupom estritamente validados)
                msg = formatar_mensagem_produto(p, cupom_aplicado)
                
                # Enviar
                sucesso = False
                status_envio = "Erro"
                try:
                    if os.path.exists(img_path):
                         sucesso = bot.enviar_imagem(img_path, msg) # Envia imagem COM legenda
                    else:
                         sucesso = bot.enviar_mensagem_texto(msg) # Fallback texto
                    
                    if sucesso:
                        status_envio = "Sucesso"
                        enviados_count += 1
                        txt_enviados.value = str(enviados_count)
                        page.update()
                except Exception as e:
                    add_log(f"Erro envio: {e}")
                
                # Salvar no DB
                salvar_historico(p['titulo'], f"WhatsApp ({fonte})", status_envio)

                # Clean up image
                if os.path.exists(img_path):
                    os.remove(img_path)
                
                time.sleep(2)

            add_log("Processo finalizado!")
            bot.fechar()
            
            # Recarrega histórico após finalizar
            load_history()

        except Exception as e:
            add_log(f"Erro no processo: {e}")
        
        txt_status.value = "Parado"
        txt_status.color = "red"
        page.process_running = False
        btn_stop.disabled = True
        btn_iniciar.disabled = False
        page.update()

    def on_click_parar(e):
        if hasattr(page, "process_running") and page.process_running:
             add_log("Parando processo... aguarde o fim do item atual.")
             page.process_running = False
             page.update()

    def on_click_iniciar(e):
        if hasattr(page, "auth_thread") and page.auth_thread.is_alive():
            add_log("Processo já está rodando!")
            return
        
        page.auth_thread = threading.Thread(target=run_shopee_process, daemon=True)
        page.auth_thread.start()

    # Dashboard Tab
    dashboard_content = ft.Column([
        ft.Text("Dashboard", size=30, weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("Produtos Enviados", size=14),
                    txt_enviados
                ]),
                padding=20,
                border_radius=10,
                bgcolor="#263238",
                expand=True
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Cupons Ativos", size=14),
                    txt_cupons
                ]),
                padding=20,
                border_radius=10,
                bgcolor="#263238",
                expand=True
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Status do Bot", size=14),
                    txt_status
                ]),
                padding=20,
                border_radius=10,
                bgcolor="#263238",
                expand=True
            ),
        ]),
        ft.Divider(),
        ft.Text("Ações Rápidas", size=20),
        ft.Row([
            ft.ElevatedButton("Iniciar Envio (Shopee + Mercado Livre)", icon="play_arrow", on_click=on_click_iniciar, ref=btn_iniciar_ref),
            ft.ElevatedButton("Atualizar Cupons", icon="sync", on_click=on_click_sync_cupons),
            ft.ElevatedButton("Parar", icon="stop", color="red", on_click=on_click_parar, disabled=True, ref=btn_stop_ref),
        ])
    ])


    import json
    from database.db import get_db_path

    # Usa o mesmo diretório permanente do banco de dados para o config.json
    CONFIG_FILE = os.path.join(os.path.dirname(get_db_path()), "config.json")

    def load_config():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(e):
        try:
            cfg = {
                "appid": input_appid.value,
                "secret": input_secret.value,
                "tag_ml": input_tag_ml.value,
                "word_ml": input_word_ml.value,
                "categoria": input_categoria.value,
                "termo_ml": input_categoria.value,
                "gemini_key": input_gemini_key.value,
                "mensagem_custom_padrao": input_custom_msg.value,
                "grupo": input_grupo.value,
                "limit": input_limit.value,
                # Scheduler Config
                "scheduler_times": scheduled_times,
                "scheduled_engagement": scheduled_engagement,
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(cfg, f)
            add_log("Configurações salvas com sucesso!")
        except Exception as ex:
            add_log(f"Erro ao salvar configurações: {ex}")

    # Load initial config
    current_config = load_config()

    # Inputs
    input_appid.value = current_config.get("appid", "")
    input_secret.value = current_config.get("secret", "")
    input_tag_ml.value = current_config.get("tag_ml", "")
    input_word_ml.value = current_config.get("word_ml", "")
    input_categoria.value = current_config.get("categoria") or current_config.get("termo_ml", "ofertas")
    input_gemini_key.value = current_config.get("gemini_key", "")
    input_custom_msg.value = current_config.get("mensagem_custom_padrao", "")
    input_grupo.value = current_config.get("grupo", "Teste")
    input_limit.value = current_config.get("limit", "5")
    
    # Config Tab
    config_content = ft.Column([
        ft.Text("Configurações", size=30, weight=ft.FontWeight.BOLD),
        ft.Text("🎯 Filtro de Nicho / Categoria Geral", size=18, weight=ft.FontWeight.BOLD, color="blue"),
        input_categoria,
        ft.Divider(),
        ft.Text("🤖 Inteligência Artificial (Google Gemini)", size=18, weight=ft.FontWeight.BOLD, color="purple"),
        input_gemini_key,
        ft.Divider(),
        ft.Text("Shopee (API)", size=18, weight=ft.FontWeight.BOLD, color="orange"),
        input_appid,
        input_secret,
        ft.Divider(),
        ft.Text("Mercado Livre (Afiliados)", size=18, weight=ft.FontWeight.BOLD, color="yellow"),
        input_tag_ml,
        input_word_ml,
        ft.Divider(),
        ft.Text("WhatsApp & Automação", size=18, weight=ft.FontWeight.BOLD, color="green"),
        input_grupo,
        input_limit,
        ft.ElevatedButton("Salvar Configurações", icon="save", on_click=save_config)
    ], scroll=ft.ScrollMode.AUTO)

    # Coupons Tab Content
    coupons_content = ft.Column([
        ft.Text("Cupons e Promoções Disponíveis", size=26, weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.ElevatedButton("Atualizar Cupons (API + ML)", icon="sync", on_click=on_click_sync_cupons),
            ft.ElevatedButton("Recarregar Tabela", icon="refresh", on_click=lambda e: load_coupons()),
        ]),
        ft.Divider(),
        ft.Text("🏷️ Cupons Ativos em Destaque:", weight=ft.FontWeight.BOLD, size=16, color="amber"),
        ft.Container(
            content=grid_coupons_cards,
            height=160,
            border=ft.border.all(1, "#37474F"),
            border_radius=8,
            padding=8,
            bgcolor="#131B24"
        ),
        ft.Divider(),
        ft.Text("📋 Tabela Completa de Cupons:", weight=ft.FontWeight.BOLD, size=16),
        ft.Container(
            content=ft.Row([coupons_table], scroll=ft.ScrollMode.ALWAYS),
            border=ft.border.all(1, "#37474F"),
            border_radius=8,
            padding=8,
            bgcolor="#1A1A1A"
        )
    ], expand=True, scroll=ft.ScrollMode.ALWAYS)

    # History Tab
    history_content = ft.Column([
        ft.Text("Histórico de Envios", size=30, weight=ft.FontWeight.BOLD),
        ft.ElevatedButton("Atualizar", icon="refresh", on_click=lambda e: load_history()),
        ft.Container(content=history_table, expand=True, border=ft.border.all(1, "grey"), border_radius=10, padding=10)
    ], expand=True, scroll=ft.ScrollMode.ALWAYS, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    # --- SCHEDULER & ENGAGEMENT LOGIC ---
    from core.engagement import gerar_mensagem_engajamento_completa

    def disparar_mensagem_engajamento_imediata(tipo, prompt_custom=""):
        """Dispara uma mensagem de engajamento no WhatsApp imediatamente para teste"""
        add_log(f"🚀 Preparando mensagem de engajamento ({tipo})...")
        try:
            msg = gerar_mensagem_engajamento_completa(
                tipo=tipo,
                prompt_custom=prompt_custom,
                api_key=input_gemini_key.value,
                log_func=add_log
            )
            add_log("Iniciando WhatsApp para envio da mensagem de engajamento...")
            bot = WhatsAppBot()
            if not bot.iniciar_driver():
                add_log("Erro ao iniciar driver do WhatsApp.")
                return
            if not bot.aguardar_login():
                add_log("Timeout no login do WhatsApp.")
                bot.fechar()
                return
            grupo = input_grupo.value or "Teste"
            if not bot.buscar_grupo(grupo):
                add_log(f"Grupo '{grupo}' não encontrado.")
                bot.fechar()
                return
            
            sucesso = bot.enviar_mensagem_texto(msg)
            bot.fechar()
            if sucesso:
                add_log("✅ Mensagem de engajamento enviada com sucesso no grupo!")
            else:
                add_log("❌ Falha ao enviar mensagem de texto no grupo.")
        except Exception as ex:
            add_log(f"Erro ao disparar engajamento: {ex}")

    def on_click_test_engajamento(e):
        tipo = select_test_eng_type.value or "versiculo"
        prompt_c = input_custom_msg.value.strip() if tipo == "custom" else ""
        threading.Thread(target=disparar_mensagem_engajamento_imediata, args=(tipo, prompt_c), daemon=True).start()

    def run_scheduler_loop(times_list, eng_list):
        add_log(f"Agendador iniciado. Horários de Ofertas: {times_list} | Engajamento: {len(eng_list)}")
        
        last_run_minute = None
        last_eng_minute = None
        last_sync_date = None

        while hasattr(page, "scheduler_running") and page.scheduler_running:
            import datetime
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            today_date = now.strftime("%Y-%m-%d")
            
            # 1. Checa Horários de Mensagens Especiais de Engajamento
            for eng_item in eng_list:
                if eng_item.get("time") == current_time and current_time != last_eng_minute:
                    add_log(f"✨ Horário de Mensagem Especial ({current_time} - {eng_item.get('label')}) atingido! Disparando...")
                    try:
                        disparar_mensagem_engajamento_imediata(eng_item.get("type", "versiculo"), eng_item.get("custom_text", ""))
                        last_eng_minute = current_time
                    except Exception as ex_eng:
                        add_log(f"Erro ao enviar mensagem agendada: {ex_eng}")

            # 2. Checa Horários de Disparo de Produtos
            if current_time in times_list and current_time != last_run_minute:
                add_log(f"📦 Horário agendado de produtos ({current_time}) atingido! Executando...")
                
                # Sincronização automática no primeiro horário do dia
                if last_sync_date != today_date:
                    add_log(f"🌅 Primeiro ciclo do dia ({today_date}). Sincronizando cupons antes do disparo...")
                    try:
                        sincronizar_todos_os_cupons(
                            appid=input_appid.value,
                            secret=input_secret.value,
                            tag_ml=input_tag_ml.value,
                            matt_word=input_word_ml.value,
                            log_func=add_log
                        )
                        load_coupons()
                        last_sync_date = today_date
                    except Exception as ex_sync:
                        add_log(f"Aviso ao sincronizar cupons do dia: {ex_sync}")

                try:
                    run_shopee_process()
                    last_run_minute = current_time
                except Exception as e:
                    add_log(f"Erro no agendador de produtos: {e}")

            # Aguarda 5s antes de checar novamente
            for _ in range(5):
                if not hasattr(page, "scheduler_running") or not page.scheduler_running:
                    break
                time.sleep(1)
        
        add_log("Agendador parado.")

    def on_click_start_scheduler(e):
        if hasattr(page, "scheduler_running") and page.scheduler_running:
            add_log("Agendador já está rodando.")
            return
        
        if not scheduled_times and not scheduled_engagement:
            add_log("Adicione pelo menos um horário de oferta ou mensagem especial.")
            return

        page.scheduler_running = True
        total_agendamentos = len(scheduled_times) + len(scheduled_engagement)
        txt_scheduler_status.value = f"Ativo ({total_agendamentos} agendamentos)"
        txt_scheduler_status.color = "green"
        btn_start_scheduler.disabled = True
        btn_stop_scheduler.disabled = False
        page.update()

        threading.Thread(target=run_scheduler_loop, args=(scheduled_times, scheduled_engagement), daemon=True).start()

    def on_click_stop_scheduler(e):
        page.scheduler_running = False
        txt_scheduler_status.value = "Parado"
        txt_scheduler_status.color = "red"
        btn_start_scheduler.disabled = False
        btn_stop_scheduler.disabled = True
        add_log("Parando agendador (aguarde)...")
        page.update()

    # Data storage for times
    scheduled_times = []
    scheduled_engagement = []
    
    def update_times_list():
        col_times.controls.clear()
        for t in scheduled_times:
            col_times.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"📦 {t}", size=15, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Icon("delete", color="white", size=15),
                            on_click=lambda e, time=t: remove_time(time),
                            padding=4,
                            ink=True,
                            border_radius=50,
                            width=28,
                            height=28,
                            alignment=ft.alignment.Alignment(0, 0),
                            bgcolor="#D32F2F"
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=8,
                    border_radius=8,
                    bgcolor="#2C2C2C",
                    border=ft.border.all(1, "#444444")
                )
            )
        page.update()

    def update_engagement_list():
        col_eng_times.controls.clear()
        for item in scheduled_engagement:
            t_str = item.get("time", "")
            lbl = item.get("label", "Mensagem Especial")
            c_txt = (item.get("custom_text") or "").strip()
            sub_lbl = f'"{c_txt[:28]}..."' if c_txt else lbl
            col_eng_times.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"⏰ {t_str} - {lbl}", size=13, weight=ft.FontWeight.BOLD, color="amber"),
                            ft.Text(sub_lbl, size=11, color="white70"),
                        ], spacing=2, expand=True),
                        ft.Container(
                            content=ft.Icon("delete", color="white", size=15),
                            on_click=lambda e, it=item: remove_eng_item(it),
                            padding=4,
                            ink=True,
                            border_radius=50,
                            width=28,
                            height=28,
                            alignment=ft.alignment.Alignment(0, 0),
                            bgcolor="#D32F2F"
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=8,
                    border_radius=8,
                    bgcolor="#1E2A38",
                    border=ft.border.all(1, "#2C4058")
                )
            )
        page.update()

    def remove_time(t):
        if t in scheduled_times:
            scheduled_times.remove(t)
            update_times_list()
            save_config(None)

    def remove_eng_item(it):
        if it in scheduled_engagement:
            scheduled_engagement.remove(it)
            update_engagement_list()
            save_config(None)

    def add_time_handler(e):
        try:
            t = input_time.value
            if not t:
                input_time.error_text = "Digite um horário"
                page.update()
                return
                
            if len(t) == 5 and t[2] == ":":
                 if t not in scheduled_times:
                     scheduled_times.append(t)
                     scheduled_times.sort()
                     input_time.value = ""
                     input_time.error_text = None
                     update_times_list()
                     save_config(None)
                 else:
                     input_time.error_text = "Horário já existe"
            else:
                 input_time.error_text = "Formato inválido (HH:MM)"
            page.update()
        except Exception as ex:
            add_log(f"Erro ao adicionar horário: {ex}")
            page.update()

    def add_eng_handler(e):
        try:
            t = input_eng_time.value
            if not t or len(t) != 5 or t[2] != ":":
                input_eng_time.error_text = "Formato (HH:MM)"
                page.update()
                return
            
            tipo = select_eng_type.value or "versiculo"
            label_map = {
                "versiculo": "📖 Versículo Bíblico do Dia",
                "dica": "💡 Dica de Economia",
                "resumo_cupons": "🏷️ Resumo de Cupons do Dia",
                "custom": "✍️ Mensagem Personalizada"
            }
            texto_custom = input_custom_msg.value.strip() if tipo == "custom" else ""
            novo_item = {
                "time": t,
                "type": tipo,
                "label": label_map.get(tipo, "Mensagem Especial"),
                "custom_text": texto_custom
            }
            # Evita duplicado no mesmo horário
            if not any(x.get("time") == t for x in scheduled_engagement):
                scheduled_engagement.append(novo_item)
                scheduled_engagement.sort(key=lambda x: x.get("time", ""))
                input_eng_time.value = ""
                input_eng_time.error_text = None
                update_engagement_list()
                save_config(None)
            else:
                input_eng_time.error_text = "Já existe mensagem neste horário"
            page.update()
        except Exception as ex:
            add_log(f"Erro ao adicionar mensagem de engajamento: {ex}")
            page.update()

    # Controles de Agendamento de Produtos
    input_time = ft.TextField(label="Horário de Ofertas (HH:MM)", width=180)
    btn_add_time = ft.ElevatedButton("Adicionar", icon="add", on_click=add_time_handler)
    col_times = ft.GridView(expand=True, max_extent=160, child_aspect_ratio=3, spacing=8, run_spacing=8)

    # Controles de Agendamento de Mensagens Especiais de Engajamento
    select_eng_type = ft.Dropdown(
        label="Tipo de Mensagem Especial",
        value="versiculo",
        width=250,
        options=[
            ft.dropdown.Option("versiculo", "📖 Versículo Bíblico do Dia"),
            ft.dropdown.Option("dica", "💡 Dica de Economia / Compras"),
            ft.dropdown.Option("resumo_cupons", "🏷️ Resumo de Cupons Ativos"),
            ft.dropdown.Option("custom", "✍️ Mensagem Personalizada"),
        ]
    )
    input_eng_time = ft.TextField(label="Horário Especial (HH:MM)", width=180)
    btn_add_eng = ft.ElevatedButton("Agendar Mensagem", icon="add_alert", on_click=add_eng_handler)
    col_eng_times = ft.GridView(expand=True, max_extent=260, child_aspect_ratio=2.2, spacing=8, run_spacing=8)

    # Botão de Teste Imediato de Mensagem Especial
    select_test_eng_type = ft.Dropdown(
        label="Testar Tipo de Mensagem",
        value="versiculo",
        width=230,
        options=[
            ft.dropdown.Option("versiculo", "📖 Versículo do Dia"),
            ft.dropdown.Option("dica", "💡 Dica de Economia"),
            ft.dropdown.Option("resumo_cupons", "🏷️ Resumo de Cupons"),
            ft.dropdown.Option("custom", "✍️ Mensagem Personalizada"),
        ]
    )
    btn_test_eng = ft.ElevatedButton("🚀 Enviar Teste Agora no WhatsApp", icon="send", on_click=on_click_test_engajamento)

    txt_scheduler_status = ft.Text("Parado", size=20, weight=ft.FontWeight.BOLD, color="red")
    btn_start_scheduler = ft.ElevatedButton("Iniciar Agendamento Geral", icon="play_arrow", on_click=on_click_start_scheduler)
    btn_stop_scheduler = ft.ElevatedButton("Parar Agendamento Geral", icon="stop", on_click=on_click_stop_scheduler, disabled=True)

    # Scheduler Content Completo (UI v1.2)
    scheduler_content = ft.Column([
        ft.Text("Agendamento Geral & Mensagens de Engajamento", size=26, weight=ft.FontWeight.BOLD),
        ft.Row([ft.Text("Status do Robô:", size=16), txt_scheduler_status]),
        ft.Divider(),
        
        # Seção 1: Ofertas de Produtos
        ft.Text("📦 1. Horários de Disparo de Ofertas (Shopee + ML):", weight=ft.FontWeight.BOLD, size=16, color="green"),
        ft.Row([input_time, btn_add_time]),
        ft.Container(content=col_times, height=90, border=ft.border.all(1, "grey"), border_radius=6, padding=6, bgcolor="#1A1A1A"),
        
        ft.Divider(),
        
        # Seção 2: Mensagens Especiais de Engajamento
        ft.Text("✨ 2. Mensagens Especiais Diárias (Versículos / Dicas / Cupons):", weight=ft.FontWeight.BOLD, size=16, color="amber"),
        input_custom_msg,
        ft.Row([select_eng_type, input_eng_time, btn_add_eng]),
        ft.Container(content=col_eng_times, height=110, border=ft.border.all(1, "grey"), border_radius=6, padding=6, bgcolor="#131B24"),
        
        ft.Divider(),
        
        # Seção 3: Teste Imediato de Engajamento
        ft.Text("🧪 Teste Rápido de Conteúdo:", weight=ft.FontWeight.BOLD, color="purple"),
        ft.Row([select_test_eng_type, btn_test_eng]),
        
        ft.Divider(),
        ft.Row([
            ft.Container(content=btn_start_scheduler, expand=True),
            ft.Container(content=btn_stop_scheduler, expand=True)
        ]),
        ft.Row([
            ft.Text("Nota: O computador deve permanecer ligado e conectado à internet.", italic=True, size=12)
        ], alignment=ft.MainAxisAlignment.CENTER)
    ], expand=True, scroll=ft.ScrollMode.ALWAYS)
    
    # Visibilidade inicial das abas
    dashboard_content.visible = True
    coupons_content.visible = False
    config_content.visible = False
    history_content.visible = False
    scheduler_content.visible = False

    # Nav Buttons
    btn_dash = ft.ElevatedButton("Dashboard", icon="dashboard")
    btn_coup = ft.ElevatedButton("Cupons", icon="local_offer")
    btn_conf = ft.ElevatedButton("Configurações", icon="settings")
    btn_hist = ft.ElevatedButton("Histórico", icon="history")
    btn_sche = ft.ElevatedButton("Agendamento", icon="schedule")

    def update_nav_styles(selected_index):
        active_color = "#455A64"
        btn_dash.style = ft.ButtonStyle(bgcolor=active_color if selected_index == 0 else None)
        btn_coup.style = ft.ButtonStyle(bgcolor=active_color if selected_index == 1 else None)
        btn_conf.style = ft.ButtonStyle(bgcolor=active_color if selected_index == 2 else None)
        btn_hist.style = ft.ButtonStyle(bgcolor=active_color if selected_index == 3 else None)
        btn_sche.style = ft.ButtonStyle(bgcolor=active_color if selected_index == 4 else None)
        page.update()

    def navigate(idx):
        dashboard_content.visible = (idx == 0)
        coupons_content.visible = (idx == 1)
        config_content.visible = (idx == 2)
        history_content.visible = (idx == 3)
        scheduler_content.visible = (idx == 4)
        if idx == 1:
            load_coupons()
        if idx == 3:
            load_history()
        if idx == 4:
            update_times_list()
        update_nav_styles(idx)
        page.update()

    btn_dash.on_click = lambda e: navigate(0)
    btn_coup.on_click = lambda e: navigate(1)
    btn_conf.on_click = lambda e: navigate(2)
    btn_hist.on_click = lambda e: navigate(3)
    btn_sche.on_click = lambda e: navigate(4)

    update_nav_styles(0)

    # Top Navigation Row
    nav_row = ft.Container(
        content=ft.Row([
            btn_dash, btn_coup, btn_conf, btn_hist, btn_sche
        ], alignment=ft.MainAxisAlignment.CENTER),
        padding=10,
        bgcolor="#111111"
    )

    # Content area
    content_area = ft.Column(
        controls=[
            dashboard_content,
            coupons_content,
            config_content,
            history_content,
            scheduler_content
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO
    )

    # Log area
    log_area = ft.Column(
        controls=[
            ft.Divider(),
            ft.Text("Logs do Sistema", size=14, weight=ft.FontWeight.BOLD, color="grey"),
            log_container
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )

    page.add(
        ft.Column(
            controls=[
                nav_row,
                ft.Divider(height=1),
                content_area,
                log_area,
            ],
            expand=True,
            spacing=0
        )
    )

    # Manual assign to ensure variables are linked to the controls in the UI tree
    btn_iniciar = dashboard_content.controls[4].controls[0]
    btn_stop = dashboard_content.controls[4].controls[2]

    # Init loads
    load_history()
    load_coupons()

    # Load Scheduler Config
    try:
        scheduled_times.extend(current_config.get("scheduler_times", []))
        scheduled_engagement.extend(current_config.get("scheduled_engagement", []))
        update_times_list()
        update_engagement_list()
    except Exception as e:
        print(f"Erro ao carregar config do agendador: {e}")

    page.update()

