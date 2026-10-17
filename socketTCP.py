import socket
import random

class SocketTCP:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = None
        self.num_sec = 0
        self.datos_faltantes = 0
        self.info_faltante = b""
        self.sec_esperada = None

    @staticmethod
    def parse_segment(segmento: bytes) -> dict:
        header = segmento[:5]
        datos = segmento[5:]

        seq = int.from_bytes(header[0:4], byteorder='big')
        flags = int.from_bytes(header[4:5], byteorder='big')

        syn = bool(flags & 4)
        ack = bool(flags & 2)
        fin = bool(flags & 1)

        return {
            'seq': seq,
            'syn': syn,
            'ack': ack,
            'fin': fin,
            'datos': datos
        }

    @staticmethod
    def create_segment(seq: int, syn: bool, ack: bool, fin: bool, datos: bytes) -> bytes:
        flags = 0
        if syn: flags += 4
        if ack: flags += 2
        if fin: flags += 1

        seq_bytes = seq.to_bytes(4, byteorder='big')
        flag_byte = flags.to_bytes(1, byteorder='big')

        return seq_bytes + flag_byte + datos

    def bind(self, address: tuple[str, int]) -> None:
        self.socket.bind(address)

    def connect(self, address: tuple[str, int]):
        self.address = address
        self.num_sec = random.randint(0,100) 
        self.socket.settimeout(1.0)
        mensaje_syn = self.create_segment(seq=self.num_sec, syn=True, ack=False, fin=False, datos=b"")
        while True:
            self.socket.sendto(mensaje_syn, self.address)
            try:
                mensaje, nueva_addr = self.socket.recvfrom(1024)
                mensaje_parseado = self.parse_segment(mensaje)
                
                if mensaje_parseado['syn'] and mensaje_parseado['ack'] and mensaje_parseado['seq'] == self.num_sec + 1:
                    self.address = nueva_addr
                    self.num_sec = mensaje_parseado['seq'] + 1
                    break
            except (TimeoutError, socket.timeout):
                print("(debug) Timeout esperando ACK")
                continue
        mensaje_ack = self.create_segment(seq=self.num_sec, syn=False, ack=True, fin=False, datos=b"")
        self.socket.sendto(mensaje_ack, self.address)
        self.socket.settimeout(None)


    def accept(self):
        self.socket.settimeout(None)
        while True:
            mensaje, client_addr = self.socket.recvfrom(1024)
            mensaje_parse = self.parse_segment(mensaje)
            
            if mensaje_parse['syn'] and not mensaje_parse['ack']:
                seq_serv = mensaje_parse['seq'] + 1
                
                nuevo_socket = SocketTCP()
                ip = self.socket.getsockname()[0]
                nuevo_socket.bind((ip, 0))
                nuevo_socket.address = client_addr
                nuevo_socket.num_sec = seq_serv
                break
        nuevo_socket.socket.settimeout(1.0)
        segmento_syn_ack = SocketTCP.create_segment(
            seq=nuevo_socket.num_sec, 
            syn=True, 
            ack=True, 
            fin=False, 
            datos=b""
        )
        while True:
            nuevo_socket.socket.sendto(segmento_syn_ack, client_addr)
            try:
                ack, _ = nuevo_socket.socket.recvfrom(1024)
                ack_parseado = SocketTCP.parse_segment(ack)
                
                if ack_parseado['ack'] and not ack_parseado['syn'] and ack_parseado['seq'] == nuevo_socket.num_sec + 1:
                    nuevo_socket.num_sec = ack_parseado['seq']
                    nuevo_socket.sec_esperada = nuevo_socket.num_sec
                    nuevo_socket.socket.settimeout(None)
                    return nuevo_socket, nuevo_socket.socket.getsockname()
            except (TimeoutError, socket.timeout):
                print("(debug) Timeout esperando ACK")
                continue

    def send(self, message):
        self.socket.settimeout(1.0)
        message_length = str(len(message)).encode("utf-8")
        while True:
            segmento_length = self.create_segment(seq=self.num_sec, syn=False, ack=False, fin=False, datos=message_length)
            self.socket.sendto(segmento_length, self.address)
            try:
                ack, _ = self.socket.recvfrom(21)
                ack_parsed = self.parse_segment(ack)
                if ack_parsed['syn'] and ack_parsed['ack']:
                    ack_handshake = self.create_segment(
                        seq= self.num_sec,
                        syn= False,
                        ack= True,
                        fin= False,
                        datos=b""
                    )
                    self.socket.sendto(ack_handshake, self.address)
                    continue
                if ack_parsed['ack'] and ack_parsed['seq'] == self.num_sec:
                    self.num_sec += 1
                    break
            except(TimeoutError, socket.timeout):
                print("(debug) Timeout esperando ACK")
                continue
        for i in range(0, len(message), 16): #Max 16 bytes
            trozo = message[i:i+16]
            while True:
                segmento = self.create_segment(seq=self.num_sec, syn=False, ack=False, fin=False, datos=trozo)
                self.socket.sendto(segmento, self.address)
                try:
                    ack, _ = self.socket.recvfrom(21)
                    ack_parsed = self.parse_segment(ack)
                    if ack_parsed['ack'] and ack_parsed['seq'] == self.num_sec:
                                        self.num_sec += 1
                                        break
                except(TimeoutError, socket.timeout):
                    print("(debug) Timeout esperando ACK")
                    continue
        self.socket.settimeout(None)

    def recv(self, buff_size):
        self.socket.settimeout(None)
        if self.datos_faltantes == 0 and len(self.info_faltante) == 0:
            while True:
                 datos, _ = self.socket.recvfrom(21)
                 datos_parsed = self.parse_segment(datos)
                 if datos_parsed['ack']:
                    continue
                 segmento_ack = self.create_segment(seq=datos_parsed['seq'], syn=False, ack=True, fin=False, datos=b"")
                 self.socket.sendto(segmento_ack, self.address)
                 if self.sec_esperada is None or datos_parsed['seq'] == self.sec_esperada:
                      self.datos_faltantes = int(datos_parsed['datos'].decode("utf-8"))
                      self.sec_esperada = datos_parsed['seq'] + 1
                      break
        while len(self.info_faltante) < buff_size and self.datos_faltantes > 0:
            datos, _ = self.socket.recvfrom(21)
            datos_parsed = self.parse_segment(datos)
            segmento_ack = self.create_segment(seq=datos_parsed['seq'], syn=False, ack=True, fin=False, datos=b"")
            self.socket.sendto(segmento_ack, self.address)
            if datos_parsed['seq'] == self.sec_esperada:
                 self.info_faltante += datos_parsed['datos']
                 self.datos_faltantes -= len(datos_parsed['datos'])
                 self.sec_esperada += 1
        largo_retorno = min(len(self.info_faltante), buff_size)
        datos_retorno = self.info_faltante[:largo_retorno]
        self.info_faltante = self.info_faltante[largo_retorno:]
        return datos_retorno

    def close(self):
        self.socket.settimeout(1.0)
        segmento_fin = self.create_segment(seq=self.num_sec, syn=False, ack=False, fin=True, datos=b"")
        flag_fin_ack = False
        timeouts = 3
        while timeouts > 0:
            self.socket.sendto(segmento_fin, self.address)
            try:
                respuesta, _ = self.socket.recvfrom(21)
                parseada = self.parse_segment(respuesta)
                if parseada['fin'] and parseada['ack']:
                    self.num_sec = parseada['seq'] + 1
                    flag_fin_ack = True
                    break
            except (TimeoutError, socket.timeout):
                print("(debug) Timeout esperando ACK")
                timeouts -= 1
                continue
        if flag_fin_ack:
            segmento_ack = self.create_segment(seq=self.num_sec, syn=False, ack=True, fin=False, datos=b"")
            for _ in range(3):
                self.socket.sendto(segmento_ack, self.address)
                try:
                    self.socket.recvfrom(21)
                except(TimeoutError, socket.timeout):
                    print("(debug) Timeout esperando ACK")
                    continue
        self.socket.settimeout(None)
        self.socket.close()

    def recv_close(self):
        self.socket.settimeout(None)
        while True:
            datos, _ = self.socket.recvfrom(21)
            datos_parseados = self.parse_segment(datos)
            if datos_parseados['fin'] and not datos_parseados['ack']:
                self.num_sec = datos_parseados['seq'] + 1
                break
            else:
                ack_repetido = self.create_segment(seq=datos_parseados['seq'], syn=False, ack=True, fin=False, datos=b"")
                self.socket.sendto(ack_repetido, self.address)
        self.socket.settimeout(1.0)
        segmento_fin_ack = self.create_segment(seq=self.num_sec, syn=False, ack=True, fin=True, datos=b"")
        intentos = 3 
        while intentos > 0:
            self.socket.sendto(segmento_fin_ack, self.address)
            try:
                datos, _ = self.socket.recvfrom(21)
                datos_parseados = self.parse_segment(datos)
                if datos_parseados['ack'] and not datos_parseados['fin'] and datos_parseados['seq'] == self.num_sec + 1:
                    break
            except (TimeoutError, socket.timeout):
                print("(debug) Timeout esperando ACK")
                intentos -= 1
                continue
        self.socket.settimeout(None)
        self.socket.close()