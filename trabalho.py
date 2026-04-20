# =========================
# TRABALHO PYTHON
# =========================

import math
import random
import csv
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import messagebox

# -------------------------
# CONSTANTE
# -------------------------
g = 9.8  # gravidade

# -------------------------
# FUNÇÕES DE CÁLCULO
# -------------------------

def calcular_tempo_voo(v0, angulo):
    ang = math.radians(angulo)
    return (2 * v0 * math.sin(ang)) / g


def calcular_altura_max(v0, angulo):
    ang = math.radians(angulo)
    return (v0**2 * (math.sin(ang)**2)) / (2 * g)


def calcular_alcance(v0, angulo):
    ang = math.radians(angulo)
    return (v0**2 * math.sin(2 * ang)) / g


# -------------------------
# GUARDAR RESULTADOS
# -------------------------

def guardar_resultados(v0, angulo, tempo, altura, alcance):
    with open("resultados.txt", "a", encoding="utf-8") as f:
        f.write("\n--- NOVO CÁLCULO ---\n")
        f.write(f"Velocidade: {v0} m/s\n")
        f.write(f"Ângulo: {angulo} graus\n")
        f.write(f"Tempo: {round(tempo,2)} s\n")
        f.write(f"Altura: {round(altura,2)} m\n")
        f.write(f"Alcance: {round(alcance,2)} m\n")


# -------------------------
# GRÁFICO ANIMADO
# -------------------------

def mostrar_grafico_animado(v0, angulo):
    ang = math.radians(angulo)

    t_total = calcular_tempo_voo(v0, angulo)
    t = np.linspace(0, t_total, 100)

    x = v0 * np.cos(ang) * t
    y = v0 * np.sin(ang) * t - 0.5 * g * t**2

    plt.figure()

    for i in range(len(x)):
        plt.cla()
        plt.plot(x[:i], y[:i])
        plt.scatter(x[i], y[i])
        plt.xlim(0, max(x))
        plt.ylim(0, max(y))
        plt.title("Simulação do Projétil")
        plt.grid()
        plt.pause(0.02)

    plt.show()


# -------------------------
# EXERCÍCIO PERSONALIZADO
# -------------------------

def calculo_personalizado():
    v0 = float(input("Velocidade (m/s): "))
    angulo = float(input("Ângulo (graus): "))

    t = calcular_tempo_voo(v0, angulo)
    h = calcular_altura_max(v0, angulo)
    alcance = calcular_alcance(v0, angulo)

    print(f"\nTempo: {round(t,2)} s")
    print(f"Altura: {round(h,2)} m")
    print(f"Alcance: {round(alcance,2)} m")

    guardar = input("Guardar resultados? (s/n): ")
    if guardar == "s":
        guardar_resultados(v0, angulo, t, h, alcance)

    grafico = input("Ver gráfico? (s/n): ")
    if grafico == "s":
        mostrar_grafico(v0, angulo)


# -------------------------
# LER CSV (QUIZ)
# -------------------------

def ler_csv(nome):
    perguntas = []
    with open(nome, encoding="utf-8") as f:
        leitor = csv.DictReader(f, delimiter=";")
        for linha in leitor:
            perguntas.append(linha)
    return perguntas


# -------------------------
# QUIZ INTERFACE BONITA
# -------------------------

def iniciar_interface(csv_file):
    perguntas = ler_csv(csv_file)

    janela = tk.Tk()
    janela.title("Quiz")
    janela.geometry("650x500")
    janela.config(bg="#121212")

    titulo = tk.Label(janela, text="QUIZ INTERATIVO",
                      font=("Arial", 20, "bold"),
                      fg="#00ffcc", bg="#121212")
    titulo.pack(pady=10)

    pontuacao_label = tk.Label(janela, text="Pontuação: 0",
                              fg="white", bg="#121212")
    pontuacao_label.pack()

    pergunta_label = tk.Label(janela, text="", wraplength=500,
                             fg="white", bg="#121212")
    pergunta_label.pack(pady=20)

    pontuacao = {"valor": 0}
    estado = {"index": 0}

    quiz = random.sample(perguntas, min(10, len(perguntas)))

    botoes = []

    def mostrar_pergunta():
        if estado["index"] >= len(quiz):
            messagebox.showinfo("Fim", f"Pontuação: {pontuacao['valor']}")
            janela.destroy()
            return

        q = quiz[estado["index"]]
        pergunta_label.config(text=q["pergunta"])

        opcoes = [q["opcao1"], q["opcao2"], q["opcao3"], q["opcao4"]]

        for i, b in enumerate(botoes):
            b.config(text=opcoes[i])

    def responder(resp):
        q = quiz[estado["index"]]

        if resp == int(q["correta"]):
            pontuacao["valor"] += 1

        pontuacao_label.config(text=f"Pontuação: {pontuacao['valor']}")
        estado["index"] += 1
        mostrar_pergunta()

    for i in range(4):
        b = tk.Button(janela, text="", width=40,
                      command=lambda i=i: responder(i+1))
        b.pack(pady=5)
        botoes.append(b)

    mostrar_pergunta()
    janela.mainloop()


# -------------------------
# MENU PRINCIPAL
# -------------------------

def menu():
    while True:
        print("\n===== MENU =====")
        print("1 - Cálculo físico")
        print("2 - Gráfico animado")
        print("3 - Quiz (interface)")
        print("0 - Sair")

        op = input("Escolha: ")

        if op == "1":
            calculo_personalizado()

        elif op == "2":
            v0 = float(input("Velocidade: "))
            angulo = float(input("Ângulo: "))
            mostrar_grafico_animado(v0, angulo)

        elif op == "3":
            iniciar_interface("perguntas.csv")

        elif op == "0":
            break

        else:
            print("Opção inválida")


# -------------------------
# INICIAR
# -------------------------
menu()