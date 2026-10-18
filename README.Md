# Control 2

Repositorio para el Control 2 del curso **Redes CC4303-1** del DCC UChile.

## Actividad 3: Stop & Wait

Para activar el servidor, desde la terminal:

```bash
python3 servidor.py
```

Para activar el cliente, desde la terminal:


```bash
python3 cliente.py localhost 8000 < archivo.txt
```

Si se quiere activar netem:

```bash
sudo tc qdisc add dev lo root netem loss 20.0% delay 0.5s
```

### No olvidar sacarlo con:

```bash
sudo tc qdisc del dev lo root netem
```

## Actividad 4: Control de congestión

### Repetir pasos de Actividad 3.