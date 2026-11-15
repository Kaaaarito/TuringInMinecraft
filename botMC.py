import threading
import time

from javascript import On, once, require

from MT import (
    ESTADO_A_COFRE,
    ESTADO_FINAL,
    TAMANO_INVENTARIO,
    DatosItem,
    clasificar_item,
    ejecutar_paso_a_paso,
)

mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')
minecraft_data = require('minecraft-data')
Vec3 = require('vec3')

HOST = 'localhost'
PUERTO = 25565
USUARIO = 'alanTurin777'
VERSION = '1.20.4'

COORDENADAS_COFRES = {
    'E': (4, -60, 0),  # herramientas, armas, armaduras y especiales
    'O': (2, -60, 0),  # comida y cultivos
    'D': (0, -60, 0),  # bloques de construcción
    'M': (-2, -60, 0),  # minerales y lingotes
}

PRIMERA_RANURA = 9
RANURAS_INVENTARIO = range(PRIMERA_RANURA, PRIMERA_RANURA + TAMANO_INVENTARIO)
DISTANCIA_COFRE = 3.0  # el jugador alcanza a abrir cofres hasta ~4.5 bloques
SEGUNDOS_MAXIMOS_CAMINATA = 30


def _existe(coleccion, clave) -> bool:
    try:
        return coleccion[clave] is not None
    except Exception:
        return False


class LectorInventario:
    def __init__(self, bot, datos_minecraft):
        self.bot = bot
        self.datos = datos_minecraft

    def leer(self):
        items = [self.bot.inventory.slots[i] for i in RANURAS_INVENTARIO]
        cadena = ''.join(clasificar_item(self._describir(item)) for item in items)
        return cadena, items

    def _describir(self, item):
        if item is None:
            return None
        nombre = str(item.name)
        return DatosItem(
            nombre=nombre,
            es_comida=_existe(self.datos.foods, item.type),
            es_bloque=_existe(self.datos.blocksByName, nombre),
            encantado=self._esta_encantado(item),
        )

    @staticmethod
    def _esta_encantado(item) -> bool:
        try:
            return len(item.enchants) > 0
        except Exception:
            return False


class DepositoCofres:
    def __init__(self, bot, coordenadas):
        self.bot = bot
        self.cofres = {categoria: Vec3(*xyz) for categoria, xyz in coordenadas.items()}

    def depositar(self, categoria, item):
        cofre = self.cofres[categoria]
        print(f"  -> Yendo al cofre '{categoria}' para guardar {item.name} x{item.count}")
        self._caminar_hasta(cofre)
        self._guardar(cofre, item)
        print(f"  -> {item.name} guardado")

    def _caminar_hasta(self, destino):
        meta = pathfinder.goals.GoalNear(destino.x, destino.y, destino.z, 2)
        self.bot.pathfinder.setGoal(meta)

        # Se mide hasta el centro del bloque del cofre, no hasta su esquina,
        # para que la distancia coincida con lo que deja GoalNear (2 bloques).
        centro = destino.offset(0.5, 0.5, 0.5)
        limite = time.time() + SEGUNDOS_MAXIMOS_CAMINATA
        while self.bot.entity.position.distanceTo(centro) > DISTANCIA_COFRE:
            if time.time() > limite:
                raise TimeoutError(f"No pude llegar al cofre en {destino}")
            time.sleep(0.2)

    def _guardar(self, cofre, item):
        ventana = self.bot.openContainer(self.bot.blockAt(cofre))
        try:
            time.sleep(0.3)
            ventana.deposit(item.type, None, item.count)
            time.sleep(0.3)
        finally:
            ventana.close()


class BotOrdenador:
    def __init__(self):
        self.bot = mineflayer.createBot({
            'host': HOST,
            'port': PUERTO,
            'username': USUARIO,
            'version': VERSION,
        })
        self.bot.loadPlugin(pathfinder.pathfinder)

        self.datos = minecraft_data(VERSION)
        self.lector = LectorInventario(self.bot, self.datos)
        self.cofres = DepositoCofres(self.bot, COORDENADAS_COFRES)
        self.ocupado = False

        self._registrar_eventos()

    def _registrar_eventos(self):
        @On(self.bot, 'spawn')
        def al_aparecer(*args):
            movimientos = pathfinder.Movements(self.bot, self.datos)
            self.bot.pathfinder.setMovements(movimientos)
            print("Bot conectado y esperando en el servidor.")
            self.bot.chat("Listo. Llena mi inventario y escribe 'ordenar' para iniciar la MNTM.")

        @On(self.bot, 'chat')
        def al_chatear(*args):
            argumentos = args if isinstance(args[0], str) else args[1:]
            self._atender_chat(argumentos[0], argumentos[1])

    def _atender_chat(self, usuario, mensaje):
        if usuario == self.bot.username:
            return

        comando = str(mensaje).strip().lower()
        if comando == 'ordenar':
            self._iniciar_ciclo()
        elif comando == 'inventario':
            cadena, _ = self.lector.leer()
            print(f"Cadena actual (|w|={len(cadena)}): {cadena}")
            self.bot.chat(f"Cadena actual: {cadena}")

    def _iniciar_ciclo(self):
        if self.ocupado:
            self.bot.chat("Ya estoy ejecutando una clasificación.")
            return
        self.ocupado = True
        threading.Thread(target=self.ejecutar_ciclo, daemon=True).start()

    def ejecutar_ciclo(self):
        try:
            cadena, items = self.lector.leer()
            print(f"\nCadena del inventario (|w|={len(cadena)}):\n  {cadena}\n")
            self.bot.chat(f"Iniciando MNTM con cadena: {cadena}")

            aceptada = False
            for paso in ejecutar_paso_a_paso(cadena):
                print(f"[Paso {paso.numero:02d}] Estado: {paso.estado}")
                print(paso.describir_cintas())
                if paso.estado in ESTADO_A_COFRE:
                    self._guardar_item(ESTADO_A_COFRE[paso.estado], items[paso.posicion], paso.posicion)
                elif paso.estado == ESTADO_FINAL:
                    aceptada = True
                    break

            if aceptada:
                print("\n=== Estado final q5 alcanzado: inventario clasificado ===")
                self.bot.chat("Estado final q5 alcanzado. Inventario ordenado.")
            else:
                print("\n=== La MNTM rechazó la cadena ===")
                self.bot.chat("La MNTM rechazó la cadena.")
        except Exception as error:
            print(f"Error durante la clasificación: {error}")
            self.bot.chat("Ocurrió un error durante la clasificación. Revisa la consola.")
        finally:
            self.ocupado = False

    def _guardar_item(self, categoria, item, posicion):
        # El inventario se leyó al inicio: se comprueba que el objeto siga
        # en su ranura antes de llevarlo al cofre.
        actual = self.bot.inventory.slots[PRIMERA_RANURA + posicion]
        if actual is None or str(actual.name) != str(item.name):
            print(f"  -> {item.name} ya no está en su ranura; se omite")
            return
        item = actual
        try:
            self.cofres.depositar(categoria, item)
        except Exception as error:
            print(f"  -> No se pudo guardar {item.name}: {error}")
            self.bot.chat(f"No pude guardar {item.name} en el cofre {categoria}.")

    def esperar(self):
        once(self.bot, 'end')


if __name__ == '__main__':
    BotOrdenador().esperar()