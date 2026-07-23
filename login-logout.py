import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import ttkbootstrap as tb
import pystray
from PIL import Image, ImageDraw

def realizar_login():
    nome = entry_nome.get().strip()
    email = entry_email.get().strip()
    
    if not nome or not email:
        messagebox.showerror("Erro", "Preencha Nome e E-mail! (Eles são necessários para registrar a autoria dos seus Commits)")
        return
    
    try:
        # Configura o Git globalmente para o aluno logado na sessão atual
        subprocess.run(["git", "config", "--global", "user.name", nome], check=True)
        subprocess.run(["git", "config", "--global", "user.email", email], check=True)
        
        messagebox.showinfo("Sucesso", "Identidade configurada!\n\nA telinha do GitHub abrirá automaticamente quando você fizer o primeiro 'git push' ou 'git clone' de um repositório privado no terminal do VS Code.")
        
        # Tenta forçar a janela de login do GitHub a abrir na hora (funciona no Git for Windows atualizado)
        subprocess.Popen("git credential-manager github login", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        
    except Exception as e:
        messagebox.showerror("Erro", str(e))

def realizar_logout():
    try:
        # 1. Remove configs globais de nome e email do Git
        subprocess.run(["git", "config", "--global", "--unset", "user.name"], stderr=subprocess.DEVNULL)
        subprocess.run(["git", "config", "--global", "--unset", "user.email"], stderr=subprocess.DEVNULL)
        
        # 2. Método Oficial do Git (Esvazia o cache interno do Git Credential Manager)
        process = subprocess.Popen(['git', 'credential', 'reject'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        process.communicate(input="protocol=https\nhost=github.com\n\n")
        
        # 3. Varredura DESTRUTIVA no Cofre do Windows (Pega senhas do Git E do VS Code)
        resultado = subprocess.run("cmdkey /list", capture_output=True, text=True, shell=True)
        
        # Lê linha por linha do cofre de senhas do Windows
        for linha in resultado.stdout.splitlines():
            if "github" in linha.lower():
                # O Windows escreve algo como: "    Destino: LegacyGeneric:target=git:https://github.com"
                # Vamos isolar apenas o nome do alvo que precisamos apagar
                partes = linha.split(":", 1)
                if len(partes) > 1:
                    alvo = partes[1].strip()
                    
                    # Remove o prefixo se ele existir para evitar erro de sintaxe
                    if alvo.startswith("LegacyGeneric:target="):
                        alvo = alvo.replace("LegacyGeneric:target=", "")
                    
                    # Executa o tiro de misericórdia na credencial encontrada
                    comando = f'cmdkey /delete:"{alvo}"'
                    subprocess.run(comando, shell=True, capture_output=True)
        
        # 4. Limpa os campos da tela do Tkinter
        entry_nome.delete(0, tk.END)
        entry_email.delete(0, tk.END)
        
        messagebox.showinfo("Sucesso", "Logout Profundo realizado!\nTodas as credenciais do Git e do VS Code foram varridas do Windows.")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao limpar a sessão: {e}")

# ==========================================
# BANDEJA DO SISTEMA (TRAY) E EVENTOS
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
    # Força um logout de segurança antes de fechar o programa totalmente
    realizar_logout()
    icon.stop()
    app.destroy()

def iniciar_tray():
    try:
        icone_img = Image.open("professor.ico")
    except:
        icone_img = criar_icone_padrao()

    menu = pystray.Menu(
        pystray.MenuItem("Abrir", mostrar_janela, default=True),
        pystray.MenuItem("Logout e Sair", sair_do_app)
    )
    
    icone_tray = pystray.Icon("GitSessao", icone_img, "Sessão Git", menu)
    icone_tray.run()

def on_closing():
    fechar_janela()

# ==========================================
# INTERFACE GRÁFICA
# ==========================================
app = tb.Window(themename="superhero")
app.title("Sessão GitHub - Lab")
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

titulo = tb.Label(frame, text="Login GitHub (Terminal Livre)", font=("Arial", 16, "bold"))
titulo.grid(row=0, column=0, columnspan=2, pady=(0, 20))

# Campos mais simples (Apenas para autoria dos commits)
tb.Label(frame, text="Seu Nome:", font=("Arial", 11)).grid(row=1, column=0, sticky='e', padx=10, pady=10)
entry_nome = tb.Entry(frame, width=35)
entry_nome.grid(row=1, column=1, pady=10, sticky="we")

tb.Label(frame, text="Seu E-mail:", font=("Arial", 11)).grid(row=2, column=0, sticky='e', padx=10, pady=10)
entry_email = tb.Entry(frame, width=35)
entry_email.grid(row=2, column=1, pady=10, sticky="we")

# Botões de Ação
btn_login = tb.Button(frame, text="Iniciar Sessão (Configurar Git)", command=realizar_login, bootstyle="success")
btn_login.grid(row=3, column=0, columnspan=2, pady=(30, 5), sticky="we")

btn_logout = tb.Button(frame, text="Fazer Logout e Apagar Credenciais", command=realizar_logout, bootstyle="danger")
btn_logout.grid(row=4, column=0, columnspan=2, pady=5, sticky="we")

label_rodape = tb.Label(app, text="Minimiza para a bandeja ao fechar no X", font=("Arial", 9, "italic"), foreground="gray")
label_rodape.pack(side="bottom", pady=10)

threading.Thread(target=iniciar_tray, daemon=True).start()
app.mainloop()