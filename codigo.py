# =========================
# trabalho_fisica.py
# =========================

import math
import matplotlib.pyplot as plt  # biblioteca para gráficos

g = 9.8


# -------------------------
# FUNÇÕES BASE
# -------------------------

def graus_para_radianos(graus):
    return math.radians(graus)


def calcular_tempo_voo(v0, angulo):
    ang = graus_para_radianos(angulo)
    return (2 * v0 * math.sin(ang)) / g


def calcular_altura_max(v0, angulo):
    ang = graus_para_radianos(angulo)
    return (v0 ** 2 * (math.sin(ang) ** 2)) / (2 * g)


def calcular_alcance(v0, angulo):
    ang = graus_para_radianos(angulo)
    return (v0 ** 2 * math.sin(2 * ang)) / g


# -------------------------
# GUARDAR RESULTADOS EM FICHEIRO
# -------------------------

def guardar_resultados(v0, angulo, t, h, alcance):
    # Abre (ou cria) um ficheiro chamado resultados.txt
    with open("resultados.txt", "a", encoding="utf-8") as f:
        f.write("----- NOVO CÁLCULO -----\n")
        f.write(f"Velocidade inicial: {v0} m/s\n")
        f.write(f"Ângulo: {angulo} graus\n")
        f.write(f"Tempo de voo: {round(t,2)} s\n")
        f.write(f"Altura máxima: {round(h,2)} m\n")
        f.write(f"Alcance: {round(alcance,2)} m\n\n")

    print("Resultados guardados no ficheiro resultados.txt ✅")


# -------------------------
# GRÁFICO DO MOVIMENTO
# -------------------------

def mostrar_grafico(v0, angulo):
    ang = graus_para_radianos(angulo)

    # Componentes da velocidade
    vx = v0 * math.cos(ang)
    vy = v0 * math.sin(ang)

    t = 0
    dt = 0.1

    xs = []  # lista de posições x
    ys = []  # lista de posições y

    while True:
        x = vx * t
        y = vy * t - 0.5 * g * t**2

        if y < 0:
            break

        xs.append(x)
        ys.append(y)

        t += dt

    # Criar gráfico
    plt.plot(xs, ys)
    plt.title("Trajetória do projétil")
    plt.xlabel("Distância (m)")
    plt.ylabel("Altura (m)")
    plt.grid()

    plt.show()


# -------------------------
# EXERCÍCIO PERSONALIZADO
# -------------------------

def exercicio_livre():
    print("\n--- Cálculo personalizado ---")

    v0 = float(input("Velocidade inicial (m/s): "))
    angulo = float(input("Ângulo (graus): "))

    t = calcular_tempo_voo(v0, angulo)
    h = calcular_altura_max(v0, angulo)
    alcance = calcular_alcance(v0, angulo)

    print(f"\nTempo de voo: {round(t,2)} s")
    print(f"Altura máxima: {round(h,2)} m")
    print(f"Alcance: {round(alcance,2)} m")

    # Pergunta se quer guardar
    guardar = input("Queres guardar os resultados? (s/n): ")
    if guardar.lower() == "s":
        guardar_resultados(v0, angulo, t, h, alcance)

    # Pergunta se quer ver gráfico
    grafico = input("Queres ver o gráfico? (s/n): ")
    if grafico.lower() == "s":
        mostrar_grafico(v0, angulo)


# -------------------------
# MENU
# -------------------------

def menu():
    while True:
        print("\n===== MENU =====")
        print("1 - Cálculo personalizado")
        print("0 - Sair")

        opcao = input("Escolhe uma opção: ")

        if opcao == "1":
            exercicio_livre()

        elif opcao == "0":
            print("Programa terminado.")
            break

        else:
            print("Opção inválida.")


menu()