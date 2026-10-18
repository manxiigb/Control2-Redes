import socket
import sys
from Actividad4 import SocketTCP
import time

host = sys.argv[1]
port = int(sys.argv[2])
address = (host, port)

mensaje = sys.stdin.buffer.read()

print(f"Iniciando conexión a {host}:{port}...")
client_socketTCP = SocketTCP()
client_socketTCP.connect(address)
print("Conexión establecida. Enviando archivo...")
client_socketTCP.set_congestion_control(True)
# Enviar el archivo completo
start_time = time.time()
client_socketTCP.send(mensaje, mode="go_back_n")
end_time = time.time()
print(f"Tiempo de envío: {end_time - start_time:.2f} segundos")
print(f"Segmentos totales enviados: {client_socketTCP.number_of_sent_segments}")
print("Archivo enviado. Iniciando cierre de conexión...")

client_socketTCP.close()
print("Conexión cerrada limpiamente desde el cliente.")