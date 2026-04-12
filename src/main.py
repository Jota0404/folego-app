# src/main.py
from financeiro import calcular_saldo, validar_valor

def menu():
    salarios = []
    despesas = []
    
    print("--- Gerenciador Financeiro CLI ---")
    # Exemplo simples de loop para entrada
    while True:
        try:
            val = float(input("Digite um salário (ou 0 para calcular): "))
            if val == 0: break
            if validar_valor(val):
                salarios.append(val)
        except ValueError as e:
            print(f"Erro: {e}")

    # Repita a lógica para despesas...
    
    saldo = calcular_saldo(salarios, despesas)
    print(f"\nSeu saldo final é: R$ {saldo:.2f}")

if __name__ == "__main__":
    menu()