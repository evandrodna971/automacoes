import flet as ft
from database.db import init_db, salvar_historico, ler_historico, obter_produtos_enviados_sucesso
import threading
import time
import os
import random
from core.shopee import buscar_ofertas_shopee_reais
from core.mercadolivre import buscar_ofertas_ml_reais
from core.whatsapp import WhatsAppBot
from core.utils import baixar_imagem, copy_image_to_clipboard

def main_app(page: ft.Page):
    page.title = "ZapFinder Automation v2.0"
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
    txt_status = ft.Text("Parado", size=40, weight=ft.FontWeight.BOLD, color="red")

    # Inputs
    input_appid = ft.TextField(label="Shopee App ID", password=True, can_reveal_password=True)
    input_secret = ft.TextField(label="Shopee Secret Key", password=True, can_reveal_password=True)
    input_tag_ml = ft.TextField(label="ML matt_tool (ex: 38835395)")
    input_word_ml = ft.TextField(label="ML matt_word / Perfil (ex: joicemagalhes)")
    input_termo_ml = ft.TextField(label="Termo de Busca Mercado Livre", value="ofertas")
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

    # --- AUTOMATION LOGIC ---
    def run_shopee_process():
        appid = input_appid.value
        secret = input_secret.value
        grupo = input_grupo.value
        tag_ml = input_tag_ml.value
        word_ml = input_word_ml.value
        termo_ml = input_termo_ml.value
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
            enviados = obter_produtos_enviados_sucesso()
            produtos_shopee = []
            produtos_ml = []

            # 1. Busca ofertas da Shopee (se credenciais preenchidas)
            if appid and secret:
                add_log("Buscando ofertas na Shopee...")
                produtos_shopee = buscar_ofertas_shopee_reais(appid, secret, limit=limit, ignore_list=enviados, log_func=add_log)
            else:
                add_log("Credenciais Shopee não fornecidas. Pulando busca Shopee...")

            # 2. Busca ofertas do Mercado Livre
            add_log(f"Buscando ofertas no Mercado Livre (Termo: '{termo_ml}')...")
            produtos_ml = buscar_ofertas_ml_reais(termo=termo_ml, tag_afiliado=tag_ml, matt_word=word_ml, limit=limit, ignore_list=enviados, log_func=add_log)

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

            # 5. Enviar Produtos
            enviados_count = 0
            for i, p in enumerate(produtos):
                # Check for stop signal
                if not getattr(page, "process_running", True):
                    add_log("Processo interrompido pelo usuário.")
                    break

                fonte = p.get('fonte', 'Shopee')
                add_log(f"Enviando {i+1}/{len(produtos)} [{fonte}]: {p['titulo'][:25]}...")
                
                # Baixar imagem
                img_path = os.path.abspath(f"temp_prod_{i}.jpg")
                if p.get('imagem_url'):
                    baixar_imagem(p['imagem_url'], img_path)
                
                # Formatar mensagem
                msg = f"*{p['titulo']}*\n\n🛍️ Origem: {fonte}\n🔥 Por: R$ {p['preco']}\n\n🛒 Compre aqui: {p['link']}"
                
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
            ft.ElevatedButton("Parar", icon="stop", color="red", on_click=on_click_parar, disabled=True, ref=btn_stop_ref),
        ])
    ])

    import json

    CONFIG_FILE = "config.json"

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
                "termo_ml": input_termo_ml.value,
                "grupo": input_grupo.value,
                "limit": input_limit.value,
                # Scheduler Config
                "scheduler_times": scheduled_times,
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
    input_termo_ml.value = current_config.get("termo_ml", "ofertas")
    input_grupo.value = current_config.get("grupo", "Teste")
    input_limit.value = current_config.get("limit", "5")
    
    # Config Tab
    config_content = ft.Column([
        ft.Text("Configurações", size=30, weight=ft.FontWeight.BOLD),
        ft.Text("Shopee (API)", size=18, weight=ft.FontWeight.BOLD, color="orange"),
        input_appid,
        input_secret,
        ft.Divider(),
        ft.Text("Mercado Livre", size=18, weight=ft.FontWeight.BOLD, color="yellow"),
        input_termo_ml,
        input_tag_ml,
        input_word_ml,
        ft.Divider(),
        ft.Text("WhatsApp & Automação", size=18, weight=ft.FontWeight.BOLD, color="green"),
        input_grupo,
        input_limit,
        ft.ElevatedButton("Salvar Configurações", icon="save", on_click=save_config)
    ], scroll=ft.ScrollMode.AUTO)

    # History Tab
    history_content = ft.Column([
        ft.Text("Histórico de Envios", size=30, weight=ft.FontWeight.BOLD),
        ft.ElevatedButton("Atualizar", icon="refresh", on_click=lambda e: load_history()),
        ft.Container(content=history_table, expand=True, border=ft.border.all(1, "grey"), border_radius=10, padding=10)
    ], expand=True, scroll=ft.ScrollMode.ALWAYS, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    # --- SCHEDULER LOGIC ---
    # --- SCHEDULER LOGIC ---
    # --- SCHEDULER LOGIC ---
    def run_scheduler_loop(times_list):
        add_log(f"Agendador iniciado. Horários: {times_list}")
        
        last_run_minute = None

        while hasattr(page, "scheduler_running") and page.scheduler_running:
            import datetime
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            
            # Verifica se já rodou neste minuto para evitar duplo disparo
            # Verifica se o horario atual esta na lista de agendados
            if current_time in times_list and current_time != last_run_minute:
                add_log(f"Horário agendado ({current_time}) atingido! Executando...")
                try:
                    run_shopee_process()
                    last_run_minute = current_time
                    # Incrementa contador (visual apenas, se tivesse)
                except Exception as e:
                    add_log(f"Erro no agendador: {e}")
            
            # Reset last_run_minute se mudou o minuto para permitir executar se tiver outro horario colado
            # (Ex: 09:00 e 09:01)
            if current_time != last_run_minute:
                 pass

            # Aguarda 5s antes de checar novamente (polling mais rapido que 30s é melhor pra não perder o minuto)
            for _ in range(5):
                if not hasattr(page, "scheduler_running") or not page.scheduler_running:
                    break
                time.sleep(1)
        
        add_log("Agendador parado.")

    def on_click_start_scheduler(e):
        if hasattr(page, "scheduler_running") and page.scheduler_running:
            add_log("Agendador já está rodando.")
            return
        
        if not scheduled_times:
            add_log("Adicione pelo menos um horário.")
            return

        page.scheduler_running = True
        txt_scheduler_status.value = f"Ativo ({len(scheduled_times)} horários)"
        txt_scheduler_status.color = "green"
        btn_start_scheduler.disabled = True
        btn_stop_scheduler.disabled = False
        page.update()

        threading.Thread(target=run_scheduler_loop, args=(scheduled_times,), daemon=True).start()

    def on_click_stop_scheduler(e):
        page.scheduler_running = False
        txt_scheduler_status.value = "Parado"
        txt_scheduler_status.color = "red"
        btn_start_scheduler.disabled = False
        btn_stop_scheduler.disabled = True
        add_log("Parando agendador (aguarde)...")
        page.update()

    # Scheduler Logic & UI
    
    # Data storage for times
    scheduled_times = []
    
    def update_times_list():
        col_times.controls.clear()
        for t in scheduled_times:
            col_times.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(t, size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Icon("delete", color="white", size=16),
                            on_click=lambda e, time=t: remove_time(time),
                            padding=5,
                            ink=True,
                            border_radius=50,
                            width=30,
                            height=30,
                            alignment=ft.alignment.Alignment(0, 0),
                            bgcolor="#D32F2F" # Red 700
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10,
                    border_radius=8,
                    bgcolor="#2C2C2C",
                    border=ft.border.all(1, "#444444")
                )
            )
        page.update()

    def remove_time(t):
        if t in scheduled_times:
            scheduled_times.remove(t)
            update_times_list()
            save_config(None) # Auto-save

    def add_time_handler(e):
        try:
            t = input_time.value
            if not t:
                input_time.error_text = "Digite um horário"
                page.update()
                return
                
            # Simple validation
            if len(t) == 5 and t[2] == ":":
                 if t not in scheduled_times:
                     scheduled_times.append(t)
                     scheduled_times.sort()
                     input_time.value = ""
                     update_times_list()
                     save_config(None) # Auto-save
                 else:
                     input_time.error_text = "Horário já existe"
            else:
                 input_time.error_text = "Formato inválido (HH:MM)"
            page.update()
        except Exception as ex:
            add_log(f"Erro ao adicionar horário: {ex}")
            page.update()

    input_time = ft.TextField(label="Horário (HH:MM)", width=150)
    btn_add_time = ft.Container(
        content=ft.Icon("add_circle", color="green"),
        on_click=add_time_handler,
        padding=10,
        ink=True,
        border_radius=50,
        width=40,
        height=40,
        alignment=ft.alignment.Alignment(0, 0)
    )
    
    col_times = ft.GridView(
        expand=True,
        runs_count=5,
        max_extent=150,
        child_aspect_ratio=3,
        spacing=10,
        run_spacing=10,
    )

    txt_scheduler_status = ft.Text("Parado", size=20, weight=ft.FontWeight.BOLD, color="red")
    btn_start_scheduler = ft.ElevatedButton("Iniciar Agendamento", icon="play_arrow", on_click=on_click_start_scheduler)
    btn_stop_scheduler = ft.ElevatedButton("Parar Agendamento", icon="stop", on_click=on_click_stop_scheduler, disabled=True)

    # Scheduler Content
    scheduler_content = ft.Column([
        ft.Text("Agendamento Automático", size=30, weight=ft.FontWeight.BOLD),
        ft.Row([ft.Text("Status:", size=16), txt_scheduler_status]),
        ft.Divider(),
        ft.Text("Adicionar Horários de Execução (Diário):"),
        ft.Row([input_time, btn_add_time]),
        ft.Text("Lista de Horários:", weight=ft.FontWeight.BOLD),
        ft.Container(
            content=col_times,
            border=ft.border.all(1, "grey"),
            border_radius=5,
            padding=5,
            bgcolor="#1A1A1A",
            expand=True # Revert to expand
        ),
        ft.Divider(),
        ft.Row([
            ft.Container(content=btn_start_scheduler, expand=True),
            ft.Container(content=btn_stop_scheduler, expand=True)
        ]),
        ft.Row([
            ft.Text("Nota: O computador deve permanecer ligado.", italic=True)
        ], alignment=ft.MainAxisAlignment.CENTER)
    ], expand=True) # Revert to expand
    
    # Visibilidade inicial das abas
    dashboard_content.visible = True
    config_content.visible = False
    history_content.visible = False
    scheduler_content.visible = False

    # Nav Buttons (definidos antes do page.add)
    btn_dash = ft.ElevatedButton("Dashboard", icon="dashboard")
    btn_conf = ft.ElevatedButton("Configurações", icon="settings")
    btn_hist = ft.ElevatedButton("Histórico", icon="history")
    btn_sche = ft.ElevatedButton("Agendamento", icon="schedule")

    def update_nav_styles(selected_index):
        active_color = "#455A64"
        btn_dash.style = ft.ButtonStyle(bgcolor=active_color if selected_index == 0 else None)
        btn_conf.style = ft.ButtonStyle(bgcolor=active_color if selected_index == 1 else None)
        btn_hist.style = ft.ButtonStyle(bgcolor=active_color if selected_index == 2 else None)
        btn_sche.style = ft.ButtonStyle(bgcolor=active_color if selected_index == 3 else None)
        page.update()

    def navigate(idx):
        dashboard_content.visible = (idx == 0)
        config_content.visible = (idx == 1)
        history_content.visible = (idx == 2)
        scheduler_content.visible = (idx == 3)
        if idx == 2:
            load_history()
        if idx == 3:
            update_times_list()
        update_nav_styles(idx)
        page.update()

    btn_dash.on_click = lambda e: navigate(0)
    btn_conf.on_click = lambda e: navigate(1)
    btn_hist.on_click = lambda e: navigate(2)
    btn_sche.on_click = lambda e: navigate(3)

    update_nav_styles(0)

    # Top Navigation Row
    nav_row = ft.Container(
        content=ft.Row([
            btn_dash, btn_conf, btn_hist, btn_sche
        ], alignment=ft.MainAxisAlignment.CENTER),
        padding=10,
        bgcolor="#111111"
    )

    # Content area - expande e controla qual aba está visível
    content_area = ft.Column(
        controls=[
            dashboard_content,
            config_content,
            history_content,
            scheduler_content
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO
    )

    # Log area - fica fixo na parte inferior, sem expandir sobre o conteúdo
    log_area = ft.Column(
        controls=[
            ft.Divider(),
            ft.Text("Logs do Sistema", size=14, weight=ft.FontWeight.BOLD, color="grey"),
            log_container
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH
    )

    # Layout principal: nav + conteúdo expandindo + log fixo embaixo
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
    btn_stop = dashboard_content.controls[4].controls[1]

    # Init load
    load_history()

    # Load Scheduler Config
    try:
        scheduled_times.extend(current_config.get("scheduler_times", []))
        update_times_list()
    except Exception as e:
        print(f"Erro ao carregar config do agendador: {e}")

    page.update()
