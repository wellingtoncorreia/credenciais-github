import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import os
import shutil
import time
import logging
import psutil
import ttkbootstrap as tb
import pystray
from PIL import Image, ImageDraw

# ==========================================
# CONFIGURAÇÕES CORPORATIVAS DO LABORATÓRIO
# ==========================================
# 1. Auditoria (Logs)
ARQUIVO_LOG = "sessao_lab_auditoria.txt"
logging.basicConfig(
    filename=ARQUIVO_LOG,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

# 2. Ambiente Efêmero (Destruição de Código)
# AVISO: Tudo dentro desta pasta será APAGADO no logout.
PASTA_PROJETOS_LAB = r"C:\Projetos_Lab" 

# 3. Controle de Sessão
TEMPO_MAXIMO_MINUTOS = 120 # Força o logout após 2 horas de aula
sessao_ativa = False

# ==========================================
# FUNÇÕES DE GOVERNANÇA E LIMPEZA
# ==========================================
def limpar_workspace_local():
    """Simula um contêiner efêmero destruindo os arquivos locais."""
    if not os.path.exists(PASTA_PROJETOS_LAB):
        try:
            os.makedirs(PASTA_PROJETOS_LAB)
        except Exception as e:
            logging.error(f"Não foi possível criar a pasta raiz: {e}")
            return

    try:
        # Varre e deleta tudo dentro da pasta de projetos
        for item in os.listdir(PASTA_PROJETOS_LAB):
            caminho_item = os.path.join(PASTA_PROJETOS_LAB, item)
            if os.path.isfile(caminho_item) or os.path.islink(caminho_item):
                os.unlink(caminho_item)
            elif os.path.isdir(caminho_item):
                shutil.rmtree(caminho_item)
        logging.info(f"Workspace físico ({PASTA_PROJETOS_LAB}) varrido e destruído.")
    except Exception as e:
        logging.error(f"Erro ao limpar arquivos do workspace: {e}")

def monitorar_recursos():
    """Roda em segundo plano: Vigiando VS Code e Timer da Sessão."""
    global sessao_ativa
    vscode_detectado = False
    tempo_inicial = time.time()
    
    while sessao_ativa:
        # 1. Checagem do Tempo de Sessão
        tempo_decorrido = (time.time() - tempo_inicial) / 60
        if tempo_decorrido >= TEMPO_MAXIMO_MINUTOS:
            logging.warning("Tempo máximo de sessão atingido. Forçando logout por segurança.")
            app.after(0, realizar_logout, True) # Executa o logout na thread principal
            break
            
        # 2. Checagem do Processo do VS Code (code.exe)
        rodando_agora = any("code.exe" in p.name().lower() for p in psutil.process_iter(['name']))
        
        if rodando_agora:
            vscode_detectado = True
        elif vscode_detectado and not rodando_agora:
            # O VS Code estava aberto, mas agora sumiu dos processos (foi fechado)
            logging.info("Fechamento do VS Code detectado. Acionando Zero Trust (Logout Automático).")
            app.after(0, realizar_logout, True)
            break
            
        time.sleep(5) # Aguarda 5 segundos antes de checar novamente para não travar a CPU

# ==========================================
# LOGIN E LOGOUT
# ==========================================
def realizar_login():
    global sessao_ativa
    nome = entry_nome.get().strip()
    email = entry_email.get().strip()
    
    if not nome or not email:
        messagebox.showerror("Erro", "Preencha Nome e E-mail.")
        return
    
    try:
        subprocess.run(["git", "config", "--global", "user.name", nome], check=True)
        subprocess.run(["git", "config", "--global", "user.email", email], check=True)
        
        # Inicia a política de rastreabilidade
        logging.info(f"--- NOVA SESSÃO INICIADA: {nome} ({email}) ---")
        
        # Garante que a pasta física do laboratório exista e esteja vazia para o novo usuário
        limpar_workspace_local()
        
        # Inicia a Thread de monitoramento invisível (Zero Trust)
        sessao_ativa = True
        threading.Thread(target=monitorar_recursos, daemon=True).start()
        
        messagebox.showinfo("Sucesso", "Sessão Aberta!\n\nAuditoria e monitoramento de segurança ativados. Se você fechar o VS Code, a sessão será encerrada automaticamente.")
        subprocess.Popen("git credential-manager github login", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        
    except Exception as e:
        logging.error(f"Falha ao iniciar sessão para {nome}: {e}")
        messagebox.showerror("Erro", str(e))

def realizar_logout(automatico=False):
    global sessao_ativa
    sessao_ativa = False # Interrompe a thread de monitoramento
    
    try:
        # 1. Configs Git
        subprocess.run(["git", "config", "--global", "--unset", "user.name"], stderr=subprocess.DEVNULL)
        subprocess.run(["git", "config", "--global", "--unset", "user.email"], stderr=subprocess.DEVNULL)
        
        # 2. Rejeição Oficial Git
        process = subprocess.Popen(['git', 'credential', 'reject'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        process.communicate(input="protocol=https\nhost=github.com\n\n")
        
        # 3. Limpeza do Cofre Windows
        resultado = subprocess.run("cmdkey /list", capture_output=True, text=True, shell=True)
        for linha in resultado.stdout.splitlines():
            if "github" in linha.lower():
                partes = linha.split(":", 1)
                if len(partes) > 1:
                    alvo = partes[1].strip()
                    if alvo.startswith("LegacyGeneric:target="):
                        alvo = alvo.replace("LegacyGeneric:target=", "")
                    subprocess.run(f'cmdkey /delete:"{alvo}"', shell=True, capture_output=True)
        
        # 4. Destruição do Ambiente Físico Local
        limpar_workspace_local()
        
        # 5. Fechamento da Auditoria
        tipo_logout = "AUTOMÁTICO (Zero Trust)" if automatico else "MANUAL"
        logging.info(f"Sessão encerrada com sucesso via mecanismo: {tipo_logout}")
        logging.info("--------------------------------------------------\n")
        
        # 6. Limpa GUI
        entry_nome.delete(0, tk.END)
        entry_email.delete(0, tk.END)
        
        if not automatico:
            messagebox.showinfo("Sucesso", "Logout Profundo realizado!\nSenhas apagadas e arquivos locais removidos.")
            
    except Exception as e:
        logging.error(f"Erro crítico durante o logout: {e}")
        if not automatico:
            messagebox.showerror("Erro", f"Erro ao limpar a sessão: {e}")

# ==========================================
# BANDEJA DO SISTEMA (TRAY) E INTERFACE
# ==========================================
def criar_icone_padrao():
    imagem = Image.new('RGB', (64, 64), color=(43, 62, 80))
    desenho = ImageDraw.Draw(imagem)
    desenho.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
    return imagem

def fechar_janela():
    app.withdraw()
    
def mostrar_janela(icon, item):
    app.after(0, app.deiconify)

def sair_do_app(icon, item):
    realizar_logout()
    icon.stop()
    app.destroy()

def iniciar_tray():
    try:
        icone_img = Image.open("professor.ico")
    except:
        icone_img = criar_icone_padrao()

    menu = pystray.Menu(
        pystray.MenuItem("Abrir Painel", mostrar_janela, default=True),
        pystray.MenuItem("Forçar Encerramento", sair_do_app)
    )
    
    icone_tray = pystray.Icon("GitSessao", icone_img, "Sessão Git - Lab", menu)
    icone_tray.run()

def on_closing():
    fechar_janela()

# Setup Tkinter
app = tb.Window(themename="superhero")
app.title("Controle de Sessão - Lab")
app.geometry("500x350")
app.protocol("WM_DELETE_WINDOW", on_closing)

try:
    app.iconbitmap("professor.ico")
except:
    pass

frame = tb.Frame(app)
frame.pack(expand=True, fill="both", padx=20, pady=20)
frame.columnconfigure(0, weight=0)
frame.columnconfigure(1, weight=1)

tb.Label(frame, text="Login GitHub (Ambiente Efêmero)", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20))

tb.Label(frame, text="Seu Nome:", font=("Arial", 11)).grid(row=1, column=0, sticky='e', padx=10, pady=10)
entry_nome = tb.Entry(frame, width=35)
entry_nome.grid(row=1, column=1, pady=10, sticky="we")

tb.Label(frame, text="Seu E-mail:", font=("Arial", 11)).grid(row=2, column=0, sticky='e', padx=10, pady=10)
entry_email = tb.Entry(frame, width=35)
entry_email.grid(row=2, column=1, pady=10, sticky="we")

btn_login = tb.Button(frame, text="Autenticar e Monitorar Sessão", command=realizar_login, bootstyle="success")
btn_login.grid(row=3, column=0, columnspan=2, pady=(30, 5), sticky="we")

btn_logout = tb.Button(frame, text="Encerrar Manualmente (Apagar Tudo)", command=lambda: realizar_logout(False), bootstyle="danger")
btn_logout.grid(row=4, column=0, columnspan=2, pady=5, sticky="we")

tb.Label(app, text="Auditoria ativa. Monitoramento em segundo plano.", font=("Arial", 8, "italic"), foreground="gray").pack(side="bottom", pady=10)

threading.Thread(target=iniciar_tray, daemon=True).start()
app.mainloop()