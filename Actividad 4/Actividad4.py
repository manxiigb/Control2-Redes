import socket
import random
from socketUDP import SocketUDP            
from slidingWindowCC import SlidingWindowCC 
import CongestionControl as cc   
           
class SocketTCP:
    def __init__(self):
        self.socket = SocketUDP()
        self.socket.set_timer_list_length(1)
        self.address = None
        self.num_sec = 0
        self.datos_faltantes = 0
        self.info_faltante = b""
        self.sec_esperada = None
        self.congestion_control_on = False
        self.ultimo_ack_enviado = None
        self.number_of_sent_segments = 0

    def set_congestion_control(self, state: bool):
        self.congestion_control_on = state

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
                    self.socket.stop_timer(0)
                    break
                else:
                    self.socket.stop_timer(0) 
            except (TimeoutError, socket.timeout):
                self.socket.stop_timer(0)
                continue
        self.socket.settimeout(-1.0)
        mensaje_ack = self.create_segment(seq=self.num_sec, syn=False, ack=True, fin=False, datos=b"")
        self.socket.sendto(mensaje_ack, self.address)

    def accept(self):
        self.socket.settimeout(-1.0)
        while True:
            mensaje, client_addr = self.socket.recvfrom(1024)
            mensaje_parse = self.parse_segment(mensaje)
            
            if mensaje_parse['syn'] and not mensaje_parse['ack']:
                seq_serv = mensaje_parse['seq'] + 1
                
                nuevo_socket = SocketTCP()
                ip = self.socket.socket_udp.getsockname()[0]
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
                    nuevo_socket.socket.stop_timer(0)
                    nuevo_socket.socket.settimeout(-1.0)
                    return nuevo_socket, nuevo_socket.socket.socket_udp.getsockname()
                else:
                    nuevo_socket.socket.stop_timer(0) 
            except (TimeoutError, socket.timeout):
                nuevo_socket.socket.stop_timer(0)
                continue

    def send(self, message, mode="stop_and_wait"):
        if mode == "stop_and_wait":
            self.send_using_stop_and_wait(message)
        elif mode == "go_back_n":
            self.send_using_go_back_n(message)
        else:
            raise ValueError(f"Modo invalido: {mode}")

    def recv(self, buff_size, mode="stop_and_wait"):
        if mode == "stop_and_wait":
            return self.recv_using_stop_and_wait(buff_size)
        elif mode == "go_back_n":
            return self.recv_using_go_back_n(buff_size)
        else:
            raise ValueError(f"Modo invalido: {mode}")

    def recv_using_stop_and_wait(self, buff_size):
        self.socket.settimeout(-1.0)
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
            if datos_parsed['ack']:
                continue
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

    def send_using_go_back_n(self, message):
        self.socket.settimeout(1.0)
        MSS = 8
        congestion_controler = cc.CongestionControl(MSS)
        message_length = str(len(message)).encode("utf-8")
        data_list = [message_length]
        for i in range(0, len(message), MSS):
            data_list.append(message[i:i+MSS])

        inicio_seq = self.num_sec
        seq_final = inicio_seq + sum(len(d) for d in data_list)

        if self.congestion_control_on:
            window_size = int(congestion_controler.get_MSS_in_cwnd())
            print(f"(debug) window_size inicial: {window_size}")
        else:
            window_size = 8

        window = SlidingWindowCC(window_size, data_list, self.num_sec)

        base_index = 0
        next_seq_index = 0
        total_segments = len(data_list)

        while base_index < total_segments:
            while next_seq_index < base_index + window_size and next_seq_index < total_segments:
                idx_in_window = next_seq_index - base_index
                seq = window.get_sequence_number(idx_in_window)
                datos = window.get_data(idx_in_window)
                segmento = self.create_segment(seq=seq, syn=False, ack=False, fin=False, datos=datos)

                if next_seq_index == base_index:
                    self.socket.sendto(segmento, self.address, timer_index=0)
                else:
                    self.socket.sendto(segmento, self.address)
                self.number_of_sent_segments += 1
                next_seq_index += 1

            try:
                ack, _ = self.socket.recvfrom(21)
                ack_parsed = self.parse_segment(ack)

                if ack_parsed['syn'] and ack_parsed['ack']:
                    ack_hs = self.create_segment(seq=inicio_seq, syn=False, ack=True, fin=False, datos=b"")
                    self.socket.sendto(ack_hs, self.address)
                    self.number_of_sent_segments += 1

                elif ack_parsed['ack']:
                    ack_seq = ack_parsed['seq']

                    pasos_totales = 0
                    for i in range(window_size):
                        s = window.get_sequence_number(i)
                        if s is not None and s == ack_seq:
                            pasos_totales = i + 1
                            break

                    if pasos_totales > 0:
                        while pasos_totales > 0:
                            pasos_actuales = min(pasos_totales, window_size)
                            window.move_window(pasos_actuales)
                            base_index += pasos_actuales
                            pasos_totales -= pasos_actuales

                            if self.congestion_control_on:
                                for _ in range(pasos_actuales):
                                    congestion_controler.event_ack_received()
                                window_size = int(congestion_controler.get_MSS_in_cwnd())
                                window.update_window_size(window_size)
                                print(f"(debug) ACK recibido. Nuevo window_size: {window_size}")

                        self.socket.stop_timer(0)

                        if base_index < next_seq_index:
                            seq_restart = window.get_sequence_number(0)
                            if seq_restart is not None:
                                datos_restart = window.get_data(0)
                                seg_restart = self.create_segment(seq=seq_restart, syn=False, ack=False, fin=False, datos=datos_restart)
                                self.socket.sendto(seg_restart, self.address, timer_index=0)
                                self.number_of_sent_segments += 1

            except (TimeoutError, socket.timeout):
                self.socket.stop_timer(0)

                if self.congestion_control_on:
                    congestion_controler.event_timeout()
                    window_size = int(congestion_controler.get_MSS_in_cwnd())
                    window.update_window_size(window_size)
                    print(f"(debug) Timeout. Nuevo window_size: {window_size}")

                next_seq_index = base_index

        self.num_sec = seq_final
        self.socket.settimeout(-1.0)
    def recv_using_go_back_n(self, buff_size):
        self.socket.settimeout(-1.0)
        
        if self.datos_faltantes == 0 and len(self.info_faltante) == 0:
            while True:
                datos, _ = self.socket.recvfrom(21)
                datos_parsed = self.parse_segment(datos)
                
                if datos_parsed['ack']:
                    continue
                    
                if self.sec_esperada is None or datos_parsed['seq'] == self.sec_esperada:
                    self.datos_faltantes = int(datos_parsed['datos'].decode("utf-8"))
                    self.sec_esperada = datos_parsed['seq'] + len(datos_parsed['datos'])
                    self.ultimo_ack_enviado = datos_parsed['seq']
                    
                    segmento_ack = self.create_segment(seq=self.ultimo_ack_enviado, syn=False, ack=True, fin=False, datos=b"")
                    self.socket.sendto(segmento_ack, self.address)
                    break
                else:
                    if self.ultimo_ack_enviado is not None:
                        segmento_ack = self.create_segment(seq=self.ultimo_ack_enviado, syn=False, ack=True, fin=False, datos=b"")
                        self.socket.sendto(segmento_ack, self.address)

        while len(self.info_faltante) < buff_size and self.datos_faltantes > 0:
            datos, _ = self.socket.recvfrom(21)
            datos_parsed = self.parse_segment(datos)
            
            if datos_parsed['ack']:
                continue
                
            if datos_parsed['seq'] == self.sec_esperada:
                self.info_faltante += datos_parsed['datos']
                self.datos_faltantes -= len(datos_parsed['datos'])
                self.sec_esperada = datos_parsed['seq'] + len(datos_parsed['datos'])
                self.ultimo_ack_enviado = datos_parsed['seq']
                
                segmento_ack = self.create_segment(seq=self.ultimo_ack_enviado, syn=False, ack=True, fin=False, datos=b"")
                self.socket.sendto(segmento_ack, self.address)
            else:
                if self.ultimo_ack_enviado is not None:
                    segmento_ack = self.create_segment(seq=self.ultimo_ack_enviado, syn=False, ack=True, fin=False, datos=b"")
                    self.socket.sendto(segmento_ack, self.address)

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
                    self.socket.stop_timer(0)
                    break
                else:
                    self.socket.stop_timer(0) 
            except (TimeoutError, socket.timeout):
                self.socket.stop_timer(0)
                timeouts -= 1
                continue
        if flag_fin_ack:
            segmento_ack = self.create_segment(seq=self.num_sec, syn=False, ack=True, fin=False, datos=b"")
            for _ in range(3):
                self.socket.sendto(segmento_ack, self.address)
                try:
                    self.socket.recvfrom(21)
                    self.socket.stop_timer(0)
                except(TimeoutError, socket.timeout):
                    self.socket.stop_timer(0)
                    continue
        self.socket.settimeout(-1.0)
        self.socket.close()

    def recv_close(self):
        self.socket.settimeout(-1.0)
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
                    self.socket.stop_timer(0)
                    break
                else:
                    self.socket.stop_timer(0) 
            except (TimeoutError, socket.timeout):
                self.socket.stop_timer(0)
                intentos -= 1
                continue
        self.socket.settimeout(-1.0)
        self.socket.close()