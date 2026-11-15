from dataclasses import dataclass
from typing import Iterator, Optional

from automata.tm.mntm import MNTM

TAMANO_INVENTARIO = 36
ESTADO_FINAL = 'q5'
ESTADO_A_COFRE = {
    'q1': 'E',  # cinta 2: herramientas y especiales
    'q2': 'O',  # cinta 3: orgánicos
    'q3': 'D',  # cinta 4: bloques de construcción
    'q4': 'M',  # cinta 5: minerales
}


class MaquinaClasificadora:
    def __init__(self):
        self.mntm = MNTM(
            states={'q0', 'q1', 'q2', 'q3', 'q4', 'q5'},
            input_symbols={'b', 'e', 'o', 'd', 'm'},
            tape_symbols={'b', 'e', 'o', 'd', 'm', 'E', 'O', 'D', 'M', '#'},
            n_tapes=5,
            transitions={
                'q0': {
                    ('b', '#', '#', '#', '#'): [
                        ('q0', (('b', 'R'), ('#', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N')))
                    ],
                    ('e', '#', '#', '#', '#'): [
                        ('q1', (('e', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N')))
                    ],
                    ('o', '#', '#', '#', '#'): [
                        ('q2', (('o', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N')))
                    ],
                    ('d', '#', '#', '#', '#'): [
                        ('q3', (('d', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N')))
                    ],
                    ('m', '#', '#', '#', '#'): [
                        ('q4', (('m', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N')))
                    ],
                    ('#', '#', '#', '#', '#'): [
                        ('q5', (('#', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N'), ('#', 'N')))
                    ],
                },
                'q1': {
                    ('e', '#', '#', '#', '#'): [
                        ('q0', (('e', 'R'), ('E', 'R'), ('#', 'N'), ('#', 'N'), ('#', 'N')))
                    ],
                },
                'q2': {
                    ('o', '#', '#', '#', '#'): [
                        ('q0', (('o', 'R'), ('#', 'N'), ('O', 'R'), ('#', 'N'), ('#', 'N')))
                    ],
                },
                'q3': {
                    ('d', '#', '#', '#', '#'): [
                        ('q0', (('d', 'R'), ('#', 'N'), ('#', 'N'), ('D', 'R'), ('#', 'N')))
                    ],
                },
                'q4': {
                    ('m', '#', '#', '#', '#'): [
                        ('q0', (('m', 'R'), ('#', 'N'), ('#', 'N'), ('#', 'N'), ('M', 'R')))
                    ],
                },
            },
            initial_state='q0',
            blank_symbol='#',
            final_states={'q5'},
        )


@dataclass(frozen=True)
class PasoMaquina:
    numero: int
    estado: str
    posicion: int


def ejecutar_paso_a_paso(cadena: str) -> Iterator[PasoMaquina]:
    mntm = MaquinaClasificadora().mntm
    for numero, configuraciones in enumerate(mntm.read_input_stepwise(cadena)):
        if not configuraciones:
            return
        config = next(iter(configuraciones))
        yield PasoMaquina(numero, config.state, config.tapes[0].current_position)


@dataclass(frozen=True)
class DatosItem:
    nombre: str
    es_comida: bool = False
    es_bloque: bool = False
    encantado: bool = False


SUFIJOS_EQUIPO = (
    '_pickaxe', '_axe', '_shovel', '_hoe', '_sword',
    '_helmet', '_chestplate', '_leggings', '_boots',
)
EQUIPO_EXACTO = frozenset({
    'bow', 'crossbow', 'trident', 'shield', 'shears', 'fishing_rod',
    'flint_and_steel', 'elytra', 'mace', 'enchanted_book',
})

SUFIJOS_CULTIVO = ('_seeds', '_sapling')
CULTIVOS_EXACTOS = frozenset({
    'wheat', 'sugar_cane', 'sugar', 'cocoa_beans', 'nether_wart', 'kelp',
    'bamboo', 'pumpkin', 'melon', 'hay_block', 'pitcher_pod', 'mangrove_propagule',
})

SUFIJOS_MINERAL = ('_ore', '_ingot', '_nugget')
MINERALES_EXACTOS = frozenset({
    'coal', 'charcoal', 'diamond', 'emerald', 'lapis_lazuli', 'redstone', 'quartz',
    'amethyst_shard', 'netherite_scrap', 'ancient_debris',
    'raw_iron', 'raw_copper', 'raw_gold',
    'iron_block', 'gold_block', 'copper_block', 'diamond_block', 'emerald_block',
    'lapis_block', 'redstone_block', 'coal_block', 'netherite_block',
    'raw_iron_block', 'raw_copper_block', 'raw_gold_block',
})


def _es_equipo(item: DatosItem) -> bool:
    return (
        item.encantado
        or item.nombre.endswith(SUFIJOS_EQUIPO)
        or item.nombre in EQUIPO_EXACTO
    )


def _es_organico(item: DatosItem) -> bool:
    return (
        item.es_comida
        or item.nombre.endswith(SUFIJOS_CULTIVO)
        or item.nombre in CULTIVOS_EXACTOS
    )


def _es_mineral(item: DatosItem) -> bool:
    return item.nombre.endswith(SUFIJOS_MINERAL) or item.nombre in MINERALES_EXACTOS


def clasificar_item(item: Optional[DatosItem]) -> str:
    """Homomorfismo de un ítem al alfabeto {b, e, o, d, m}."""
    if item is None:
        return 'b'
    if _es_equipo(item):
        return 'e'
    if _es_organico(item):
        return 'o'
    if _es_mineral(item):
        return 'm'
    if item.es_bloque:
        return 'd'
    return 'e'


if __name__ == '__main__':
    cadena = 'eodmbd' * (TAMANO_INVENTARIO // 6)
    print(f"Cadena de entrada (|w|={len(cadena)}): {cadena}\n")

    aceptada = False
    for paso in ejecutar_paso_a_paso(cadena):
        print(f"[Paso {paso.numero:02d}] Estado: {paso.estado} | Cabezal cinta 1: {paso.posicion}")
        aceptada = paso.estado == ESTADO_FINAL

    print(f"\nCadena {'aceptada' if aceptada else 'rechazada'}")