from cryptography.fernet import Fernet

key = b"9xgyXvwEFI-nXsfpjvZJ5LRHt7Qx_Ca297AuSb8HHDA="
f = Fernet(key)

cpfs = [
    ("11111111111", "João Silva"),
    ("22222222222", "Maria Oliveira"),
    ("33333333333", "Pedro Santos"),
    ("44444444444", "Ana Costa"),
    ("38305184803", "Victor Monteiro")
]

for cpf, nome in cpfs:
    enc = f.encrypt(cpf.encode()).decode()
    print(f"{enc} -> {nome}")
