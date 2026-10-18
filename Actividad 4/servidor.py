import socket
from Actividad4 import SocketTCP

ip = '127.0.0.1'
port = 8000
address = (ip, port)

print(f"Iniciando servidor en {ip}:{port}...")
server_socketTCP = SocketTCP()
server_socketTCP.bind(address)

print("Esperando conexión de un cliente...")
connection_socketTCP, new_address = server_socketTCP.accept()
print(f"Conexión aceptada desde {new_address}. Preparando para recibir...")

print("\n--- RECIBIENDO ARCHIVO ---")
archivo_completo = b""
buff_size = 4096 

chunk = connection_socketTCP.recv(buff_size, mode="go_back_n")
archivo_completo += chunk

while connection_socketTCP.datos_faltantes > 0 or len(connection_socketTCP.info_faltante) > 0:
    chunk = connection_socketTCP.recv(buff_size, mode="go_back_n")
    archivo_completo += chunk

nombre_salida = "archivo_recibido.txt"
with open(nombre_salida, "wb") as f:
    f.write(archivo_completo)

print("\n--- RESULTADO DE LA TRANSFERENCIA ---")
print(f"Bytes totales recibidos: {len(archivo_completo)}")
print(f"El archivo se ha guardado exitosamente como '{nombre_salida}'")

print("\nEsperando cierre de conexión...")
connection_socketTCP.recv_close()
print("Conexión cerrada limpiamente desde el servidor.")