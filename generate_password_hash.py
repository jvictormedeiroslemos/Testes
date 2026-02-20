"""
Gerador de Hash de Senha para o Sistema Financeiro.

Execute este script UMA VEZ para gerar o hash SHA-256 da sua senha.
Em seguida, copie o hash gerado para o arquivo .streamlit/secrets.toml.

Uso:
    python generate_password_hash.py
"""

import hashlib
import getpass


def main():
    print("=" * 60)
    print("  Gerador de Hash de Senha — Sistema Financeiro")
    print("=" * 60)
    print()
    print("ATENÇÃO: Escolha uma senha forte (mínimo 8 caracteres).")
    print("Esta senha será usada para acessar seus dados financeiros.")
    print()

    while True:
        senha = getpass.getpass("Digite a senha desejada: ")
        if len(senha) < 8:
            print("❌ A senha deve ter pelo menos 8 caracteres. Tente novamente.\n")
            continue

        confirmacao = getpass.getpass("Confirme a senha: ")
        if senha != confirmacao:
            print("❌ As senhas não coincidem. Tente novamente.\n")
            continue

        break

    hash_gerado = hashlib.sha256(senha.encode()).hexdigest()

    print()
    print("=" * 60)
    print("  Hash gerado com sucesso!")
    print("=" * 60)
    print()
    print("Copie a linha abaixo para o seu arquivo .streamlit/secrets.toml:")
    print()
    print(f'PASSWORD_HASH = "{hash_gerado}"')
    print()
    print("Exemplo completo de .streamlit/secrets.toml:")
    print("-" * 60)
    print(f'PASSWORD_HASH = "{hash_gerado}"')
    print('ANTHROPIC_API_KEY = "sk-ant-..."   # opcional')
    print("-" * 60)
    print()
    print("IMPORTANTE: Nunca compartilhe o arquivo secrets.toml.")
    print("Ele já está no .gitignore e NÃO será enviado ao GitHub.")


if __name__ == "__main__":
    main()
