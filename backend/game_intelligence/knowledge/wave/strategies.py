"""
Biblioteca universal de Wave Management.

Las 6 técnicas fundamentales de gestión de oleada.
Los campeones referencian estas estrategias por ID. Nunca duplican el conocimiento.
"""

from backend.game_intelligence.models.wave import WaveStrategy, WaveTechnique

STRATEGIES: list[WaveStrategy] = [
    WaveStrategy(
        id="freeze",
        name="Freeze (Congelar)",
        technique=WaveTechnique.FREEZE,
        description=(
            "Mantener la oleada entre la mitad del carril y tu propia torre, "
            "preferiblemente justo fuera de su rango. El equilibrio de tropas "
            "es de +1 a +3 tropas enemigas sobre las tuyas."
        ),
        when_to_use=(
            "Cuando ganaste un intercambio y el enemigo está bajo de vida o recall. "
            "Cuando el enemigo tiene objetivos de farm fácil (push). "
            "Cuando quieres negar CS al retornar de base. "
            "Cuando su jungla está del lado contrario del mapa."
        ),
        when_not_to_use=(
            "Cuando tu jungla te quiere dañar — la oleada debe estar empujada. "
            "Cuando tienes un dive amenazante de 2v1. "
            "Cuando necesitas empujar para rotar. "
            "Cuando estás muy por delante y quieres romper estructuras."
        ),
        why=(
            "Fuerza al enemigo a sobreextenderse para recuperar farm, "
            "creando ventanas de ganks para tu jungla y presión psicológica constante."
        ),
        steps=[
            "Mata las tropas enemigas justo a tiempo para que no dañen las tuyas.",
            "Mantén el equilibrio dejando que 2-3 tropas enemigas de más estén vivas.",
            "Posiciónate lejos de la zona de ataque enemiga pero cerca de la oleada.",
            "No te excedas atacando — deja que las torretas no interfieran.",
            "Mantén la posición hasta que el enemigo falle al intentar romper el freeze.",
        ],
        common_mistakes=[
            "Atacar demasiadas tropas enemigas y perder el freeze.",
            "No posicionarse en el camino del enemigo para bloquear su acceso.",
            "Intentar freeze con demasiadas pocas tropas propias.",
            "Mantener freeze cuando el jungla enemigo está acercándose.",
            "Perder el freeze por atacar tropas por instinto.",
        ],
        tips=[
            "El freeze es más poderoso cuando el enemigo tiene alto poke — lo fuerza a ir a golpes.",
            "Avisa al jungla cuando tengas freeze activo para coordinar dives.",
            "Un freeze cerca de tu torre es la posición más segura del carril.",
            "Aprende los números de tropas: necesitas más de 1.5x tropas enemigas que propias.",
        ],
        difficulty="medium",
        drill_id="wave_freeze_fundamentals",
    ),

    WaveStrategy(
        id="slow_push",
        name="Slow Push (Empuje Lento)",
        technique=WaveTechnique.SLOW_PUSH,
        description=(
            "Acumular una oleada grande lentamente matando las tropas de cañón "
            "del enemigo y dejando que las meleé empujen solas. "
            "Crea una oleada enorme que llega a la torre enemiga."
        ),
        when_to_use=(
            "Antes de teleportar o ir a un objetivo — la oleada hará presión por ti. "
            "Para forzar al enemigo a quedarse en carril. "
            "Después de un recall exitoso para mantener presión. "
            "Cuando quieres configurar una oleada de presión lenta mientras farmeas objetivos."
        ),
        when_not_to_use=(
            "Cuando el enemigo tiene clear rápido (Sivir, Taliyah). "
            "Cuando estás en peligro de ser diveado con esa oleada."
        ),
        why=(
            "Una oleada grande llega a torre con más tropas que el enemigo puede clearar, "
            "forzando que algunas lleguen a torre. Crea ventanas de tiempo para objetivos."
        ),
        steps=[
            "Mata únicamente las tropas de cañón enemigas — deja que las meleé choquen.",
            "Las meleé propias naturalmente empujan hacia la torre enemiga.",
            "Añade magia/ranged para acelerar la acumulación si es necesario.",
            "No ataque las tropas enemigas meleé — deja que la oleada se acumule.",
            "Una vez la oleada está grande, ejecuta tu macro (TP, objetivo, recall).",
        ],
        common_mistakes=[
            "Matar tropas meleé enemigas en lugar de solo las de cañón.",
            "No aprovechar la ventana de tiempo que crea la oleada.",
            "Construir un slow push cuando el enemigo tiene clear AoE.",
            "Olvidar empujar la oleada a torre antes de un objetivo.",
        ],
        tips=[
            "El slow push es más efectivo cuanto más lento el clear del enemigo.",
            "Coordinarlo con el jungla para hacer Baron/Dragon mientras la ola presiona.",
            "Aprende a leer cuántos segundos de ventana te da según el tamaño de la oleada.",
        ],
        difficulty="medium",
        drill_id="wave_slow_push_timing",
    ),

    WaveStrategy(
        id="fast_push",
        name="Fast Push (Empuje Rápido)",
        technique=WaveTechnique.FAST_PUSH,
        description=(
            "Clearar la oleada enemiga lo más rápido posible usando todas tus habilidades "
            "para llegar a la torre enemiga inmediatamente y luego hacer recall o rotar."
        ),
        when_to_use=(
            "Cuando quieres hacer recall sin perder farm — push y baja. "
            "Cuando necesitas rotar rápidamente a otro carril. "
            "Cuando tienes ventaja y quieres forzar la torre. "
            "Después de matar al enemigo para maximizar el daño de oleada."
        ),
        when_not_to_use=(
            "Cuando tu carril está perdido y overextender es peligroso. "
            "Cuando el enemigo tiene teleport y puede responder. "
            "Cuando la jungla enemiga está cerca."
        ),
        why=(
            "Clearar rápido libera tiempo en el mapa. "
            "Genera presión de torre inmediata y crea ventanas de recall seguro."
        ),
        steps=[
            "Usa todas tus habilidades de clear para matar tropas en el menor tiempo.",
            "Lleva la oleada a la torre — deja que la torre desgaste las tropas.",
            "Haz recall, rota o busca pelea mientras el enemigo está clearando.",
            "Vuelve antes de que tu propia oleada llegue de vuelta a tu torre.",
        ],
        common_mistakes=[
            "Hacer fast push sin rotar o hacer recall después.",
            "Overextender al hacer fast push sin visión.",
            "Olvidar que el enemigo también hará fast push de vuelta.",
        ],
        tips=[
            "Lleva la oleada exactamente hasta la torre, no más lejos.",
            "El fast push más la rotación es la base del macro de top laner moderno.",
            "Aprende cuánto tiempo tienes después del push antes de que tu oleada regrese.",
        ],
        difficulty="low",
        drill_id="wave_fast_push_and_rotate",
    ),

    WaveStrategy(
        id="bounce",
        name="Bounce (Rebotar)",
        technique=WaveTechnique.BOUNCE,
        description=(
            "Construir una oleada grande empujando, dejar que la oleada enemiga "
            "que responde sea mayor, y hacer que esa oleada enorme 'rebote' "
            "de vuelta hacia tu torre en estado de freeze natural."
        ),
        when_to_use=(
            "Después de matar a un enemigo con oleada en su favor. "
            "Para configurar un freeze pasivo sin esfuerzo activo. "
            "Cuando acabas de hacer recall y quieres reestablecer control de oleada."
        ),
        when_not_to_use=(
            "Cuando el enemigo puede clearar eficientemente antes de que rebote. "
            "Cuando estás tan por delante que el freeze no tiene valor."
        ),
        why=(
            "Una oleada rebotada naturalmente se convierte en freeze "
            "sin que tengas que gestionar activamente el equilibrio. "
            "Es el método más eficiente de establecer control de oleada post-kill."
        ),
        steps=[
            "Empuja la oleada a la torre enemiga después de un kill o ventaja.",
            "Deja que la oleada enemiga responda — se acumula mientras tú farmeas.",
            "La oleada grande vuelve hacia tu torre en 'bounce'.",
            "Recíbela lejos de la torre para establecer el freeze.",
        ],
        common_mistakes=[
            "No esperar a que la oleada rebote — intentar freezar manualmente.",
            "Empujar demasiado lejos y no poder volver a tiempo para el bounce.",
            "Perder el bounce porque el enemigo clearó rápido.",
        ],
        tips=[
            "Un bounce bien ejecutado da la misma posición que un freeze sin esfuerzo.",
            "El timing del bounce depende de cuántas tropas llevas a la torre.",
        ],
        difficulty="medium",
        drill_id="wave_bounce_setup",
    ),

    WaveStrategy(
        id="crash",
        name="Crash (Romper/Volcar)",
        technique=WaveTechnique.CRASH,
        description=(
            "Llevar activamente toda la oleada a la torre enemiga en el momento exacto "
            "para maximizar el daño a la torre y crear tiempo libre en el mapa. "
            "Generalmente combinado con un recall, TP, o rotación."
        ),
        when_to_use=(
            "Para hacer recall cuando el enemigo está en base — sin perder farm. "
            "Justo antes de un objetivo mayor (Dragon, Baron, Herald). "
            "Después de un intercambio favorable para forzar la torre. "
            "Para responder a un TP del enemigo con TP propio desde base."
        ),
        when_not_to_use=(
            "Sin visión de la jungla enemiga cerca. "
            "Cuando no tienes un plan claro para después del crash. "
            "Cuando el enemigo tiene recall muy rápido."
        ),
        why=(
            "Crashear una oleada correctamente es el fundamento del macro de top laner. "
            "Cada crash ejecutado bien genera oro, tiempo libre, y ventaja estructural."
        ),
        steps=[
            "Empuja activamente con habilidades para llevar la oleada a la torre.",
            "Lleva las tropas meleé primero para maximizar el daño a torre.",
            "Asegúrate de que la oleada llega a la torre mientras tú ya estás retrocediendo.",
            "Ejecuta tu macro (recall/TP/rotar) inmediatamente después del crash.",
            "Vuelve para la próxima oleada en tu propia torre.",
        ],
        common_mistakes=[
            "Crashear sin plan de rotación o recall.",
            "Quedarse en carril después del crash sin hacer nada.",
            "Crashear cuando el jungla enemigo está cerca.",
            "No matar las tropas de cañón antes de irse — el crash no es limpio.",
        ],
        tips=[
            "El crash perfecto ocurre cuando la torre mata la última tropa justo cuando sales del carril.",
            "Aprende los 'crash windows' de tu campeón con cada nivel de poder.",
            "Crashear antes del 6 es diferente al crashear después del 6.",
        ],
        difficulty="low",
        drill_id="wave_crash_timing",
    ),

    WaveStrategy(
        id="reset",
        name="Reset (Resetear/Equilibrar)",
        technique=WaveTechnique.RESET,
        description=(
            "Llevar la oleada a una posición neutra en el centro del carril "
            "para que ambos lados tengan el mismo número de tropas. "
            "Se usa para re-establecer control cuando la oleada está en mal estado."
        ),
        when_to_use=(
            "Cuando la oleada está en tu torre y no puedes freezar. "
            "Cuando ambos llegan de recall al mismo tiempo. "
            "Para 'limpiar' una situación de oleada descontrolada. "
            "Al inicio del carril después del primer recall."
        ),
        when_not_to_use=(
            "Cuando tienes una ventaja clara y puedes ejecutar otra técnica más agresiva. "
            "Cuando el enemigo puede negar el reset con un wave clear."
        ),
        why=(
            "Una oleada equilibrada en el centro da tiempo para farmear sin riesgo, "
            "y crea una base limpia para ejecutar otras técnicas."
        ),
        steps=[
            "Mata tropas de forma equitativa en ambos bandos.",
            "Posiciona la oleada en el centro del carril.",
            "Una vez equilibrada, decide qué técnica usar a continuación.",
        ],
        common_mistakes=[
            "Resetear cuando podrías establecer ventaja directamente.",
            "No tener un plan después del reset.",
        ],
        tips=[
            "El reset es la 'posición neutral' — úsalo como punto de partida.",
            "Después de un reset exitoso, piensa qué técnica tiene más valor.",
        ],
        difficulty="low",
        drill_id=None,
    ),
]

# Índice por ID para acceso O(1)
STRATEGIES_BY_ID: dict[str, WaveStrategy] = {s.id: s for s in STRATEGIES}
