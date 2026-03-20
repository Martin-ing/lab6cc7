# Lab006 — Smart Parking Lot System

Simulación de un estacionamiento inteligente usando **C con pthreads** para la concurrencia y **Python con tkinter** para el dashboard en tiempo real. El programa en C simula 10 carros compitiendo por 3 espacios, usando semáforos para controlar el acceso y mutexes para proteger recursos compartidos. Python lee el log generado por C en tiempo real y actualiza la interfaz gráfica.


## Cómo Ejecutar

Ambos archivos (`parking.c` y `dashboard_v1.py`) deben estar en el mismo directorio.

El dashboard compila y ejecuta el C automáticamente con subprocess
```bash
python3 dashboard_v1.py
```


## Librerías en C

| Librería | Propósito |
|---|---|
| `stdio.h` | Entrada/salida|
| `stdlib.h` | malloc, free, srand, rand |
| `pthread.h` | Threads|
| `semaphore.h` | Semáforos: sem_wait, sem_post |
| `time.h` | Tiempo|
| `unistd.h` | syscalls |

### Funciones importantes de las librerías

**`time()` / `time_t`**
Retorna los segundos transcurridos desde el 1 enero 1970 como un entero (solo segundos).
```c
time_t now = time(NULL);
```

**`strftime()`**
Formatea el `struct tm` como string usando especificadores, igual que `printf` pero para fechas.
```c
strftime(buf, sizeof(buf), "%a %b %d %H:%M:%S %Y", tm_info);
// resultado: "Fri Mar 21 13:38:46 2025"
```

**`sem_wait()` / `sem_post()`**
`sem_wait` decrementa el semáforo. Si ya es 0, bloquea el thread automáticamente hasta que alguien haga `sem_post`. `sem_post` incrementa el semáforo y despierta al siguiente thread en espera.


## Funciones del Programa en C

### `log_event(const char *message)`
Registra un evento con timestamp lo imprime y lo registra en `parking_log.txt` (logging).

Realiza un lock para poder escribir de forma exlusiva al archivo.

### `car_thread(void *arg)`
Función principal de cada thread. Simula el ciclo completo: llegar, esperar, estacionarse y salir.

Realiza un sem_wait() y un lock para poder modificar correctamente cars_parked y wait_time, este lock aplica solo a la actualizacion de esas variables, si otro carro llegara a parquearse lo primero que hara será imprimir el mensaje de que se estaciono aunque inmediatamente no pueda actualziar las variables, y al salir del parqueo ya termino anteriormente con el lock entonces puede salir inmediatamente.

### `main(void)`
Inicializa todos los recursos, crea los threads, une los threads y reporta estadísticas finales.


## Implementación de Locks (Mutex)

Se usan **dos mutex separados** para permitir mayor paralelismo que usar uno solo.

### `log_mutex` — Protección del Log

Protege las escrituras al archivo. Sin este mutex, dos threads podrían escribir al mismo tiempo y el resultado sería que un thread comenzó a escribir encima del mensaje del thread anterior.

Con el mutex, solo un thread puede estar dentro de `log_event()` a la vez. Los demás se bloquean en `pthread_mutex_lock()` sin consumir CPU y se despiertan solos cuando el mutex se libera.

### `stats_mutex` — Protección de Contadores

Protege `cars_parked` y `wait_time`. Sin mutex habría una **race condition**: si dos threads leen `cars_parked = 5` al mismo tiempo y ambos hacen `cars_parked++`, ambos escribirían 6 en lugar de 7.

### Puntero al archivo y escritura ordenada

El archivo se maneja a través del puntero global `FILE *log_f`. Todas las escrituras pasan por `log_event()` que siempre adquiere `log_mutex` primero, garantizando que las líneas se escriban completas y en orden. El `fflush(log_f)` después de cada `fprintf()` fuerza que el buffer del SO se vacíe a disco inmediatamente para que Python pueda leerlo en tiempo real.

---

## Librerías en Python

| Librería | Propósito |
|---|---|
| `tkinter` | GUI |
| `threading` | Thread separado para leer el log sin bloquear la UI |
| `re` | Expresiones regulares para parsear el log |
| `subprocess` | Compilar y ejecutar el programa C |
| `os` | Verificar existencia del archivo de log |
| `time` | sleep() para el loop del watcher |

---

## Funciones del Dashboard en Python

### `__init__(self, root)`
Constructor. Inicializa el estado interno, construye la UI, compila y ejecuta el codigo en c, y arranca el watcher.

### `_compile_and_run(self)`
Compila `parking.c` con `subprocess.run()` (espera a que gcc termine) y luego lanza el ejecutable con `subprocess.Popen()`. 

### `_watch_log(self)`
Corre en un thread separado. Espera a que exista `parking_log.txt`, luego lo lee línea por línea con `readline()` en un loop. Cuando `readline()` retorna string vacío significa que no hay líneas nuevas, espera 50ms y reintenta.

Usa `root.after(0, self._process_line, line)` para actualizar la UI desde el thread secundario de forma segura, ya que tkinter no es thread-safe y no permite modificar widgets desde threads que no sean el principal.

### `_process_line(self, line)`
Analiza cada línea con expresiones regulares y actualiza el estado del dashboard según el evento detectado.

### `_update_car(self, cid, text, bg, fg)`
Actualiza visualmente la tarjeta de un carro: cambia el color de fondo del frame, el color del borde (`highlightbackground`) y el texto mostrado.

### `_refresh_spots(self)`
Actualiza el color y texto de cada spot físico y el contador de Free Spots.

### `_refresh_stats(self)`
Recalcula los cuatro contadores: spots libres, carros estacionados, carros esperando y tiempo promedio.

### `_append_log(self, line)`
Agrega una línea al widget de Text con el color correspondiente usando tags de tkinter: `arrive`=azul, `parked`=verde, `leaving`=amarillo, `stats`=rojo.

## Expresiones Regulares

Se usan en `_process_line()` para extraer información de cada línea del log. `re.search()` retorna `None` si no hay match, por lo que los `if/elif` verifican primero antes de acceder a los grupos.

## Flujo Completo del Sistema

```
python3 dashboard_v1.py
        │
        ├── subprocess.run(gcc parking.c -o parking)
        │   └── espera a que compile
        │
        ├── subprocess.Popen(./parking)
        │   └── C corre en background → escribe parking_log.txt con fflush
        │
        └── _watch_log() en thread
            └── readline() detecta líneas nuevas
                └── root.after() → _process_line() en thread principal
                    └── regex extrae evento → actualiza UI
```
