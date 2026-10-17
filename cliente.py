import socket
import sys
from socketTCP import SocketTCP

host = sys.argv[1]
port = int(sys.argv[2])
address = (host, port)

mensaje = sys.stdin.buffer.read()

print(f"Iniciando conexión a {host}:{port}...")
client_socketTCP = SocketTCP()
client_socketTCP.connect(address)
print("Conexión establecida. Enviando archivo...")

# Enviar el archivo completo
client_socketTCP.send(mensaje)
print("Archivo enviado. Iniciando cierre de conexión...")

client_socketTCP.close()
print("Conexión cerrada limpiamente desde el cliente.")