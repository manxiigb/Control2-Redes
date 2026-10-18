import socket
from socketTCP import SocketTCP

ip = '127.0.0.1'
port = 8000
address = (ip, port)

print(f"Iniciando servidor en {ip}:{port}...")
server_socketTCP = SocketTCP()
server_socketTCP.bind(address)

print("Esperando conexión de un cliente...")
connection_socketTCP, new_address = server_socketTCP.accept()
print(f"Conexión aceptada desde {new_address}. Preparando para recibir...")

n = 17 
print(f"\n--- INICIANDO PRUEBA 2n (n={n}) ---")
print(f"Llamando a recv({n}) por primera vez...")
mitad_1 = connection_socketTCP.recv(n)

print(f"Llamando a recv({n}) por segunda vez...")
mitad_2 = connection_socketTCP.recv(n)

archivo_completo = mitad_1 + mitad_2

print("\n--- RESULTADO DE LA PRUEBA ---")
print("Mitad 1 (bytes):", len(mitad_1), "->", mitad_1)
print("Mitad 2 (bytes):", len(mitad_2), "->", mitad_2)
print("Archivo completo:", archivo_completo.decode('utf-8'))
if len(archivo_completo) == 34:
    print("Prueba 2n: PASSED")
else:
    print("Prueba 2n: FAILED")

print("\nEsperando cierre de conexión...")
connection_socketTCP.recv_close()
print("Conexión cerrada limpiamente desde el servidor.")