import asyncio
import json
from openai import AsyncOpenAI

with open("api_keys_modelos.json", 'r') as f:
    creds = json.load(f)
    api_key = creds['openrouter']['api-key']


# Configuración de OpenRouter
# Asegúrate de tener tu API Key en las variables de entorno o cámbiala aquí
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)


async def generar_storytelling(df, tema_query):
    """Envía un resumen de sentimientos a DeepSeek para obtener una conclusión."""
    if client is None or df.empty:
        return "Storytelling no disponible (falta conexión a API o datos)."

    print(f"--- Generando storytelling con openai/gpt-oss-120b ---")

    resumen = df['sentimiento'].value_counts().to_dict()
    prompt = f"Analiza estos resultados de sentimiento sobre el tema '{tema_query}': {resumen}. Dame una conclusión breve, analítica y profesional sobre la opinión pública."

    try:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        resultado = response.choices[0].message.content

        #print(f"Respuesta del modelo:\n{resultado}")
        print("\n--- Storytelling generado ---")
        await asyncio.sleep(2)
        return resultado
    except Exception as e:
        print(f"Error en el storytelling: {e}")
        return "La IA no pudo procesar el resumen en este momento."


async def procesar_sentimientos(data, batch_size, red_social, semaphore):
    resultados_totales = []
    resultado = ""
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        print(f"[{red_social}] Procesando batch {i//batch_size + 1} de {len(data)//batch_size + 1}...")

        async with semaphore:
            resultado_batch = await analizar_comentarios(batch, red_social)
            resultado += resultado_batch
            #resultados_totales.append(resultado_batch)

        # Pequeña pausa para evitar bloqueos por Rate Limit de la API gratuita
            await asyncio.sleep(3)
    resultados_totales = resultado.splitlines()
    return resultados_totales


async def analizar_comentarios(comentarios, red_social):
    print(f"--- [{red_social}] Analizando con openai/gpt-oss-120b ---")

    prompt = (
        "Analiza la siguiente lista de comentarios extraídos de Instagram. "
        "Para cada comentario en la lista, realiza lo siguiente:\n"
        "1. Clasifica el sentimiento como 'Positivo', 'Negativo' o 'Neutro', solo con esas clases.\n"
        "2. Proporciona una explicación breve y técnica de la clasificación.\n\n"
        "Dame en este formato: comentario|sentimiento|explicacion\n\n"
        f"Lista de comentarios: {comentarios}"
    )

    try:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        resultado = response.choices[0].message.content

        #print(f"Respuesta del modelo:\n{resultado}")
        print("\n--- Analisis finalizado ---")
        asyncio.sleep(2)
        return resultado

    except Exception as e:
        print(f"\n[!] Error detectado: {e}")
        if "429" in str(e):
            print("Limite de peticiones por minuto alcanzado, esperando 10 segundos")
            await asyncio.sleep(10)
        return ""

if __name__ == "__main__":
    comentarios_extraidos = [
        "libertad para venezuela, amen",
        "nisiquiera han dado una fecha de vida",
        "liberen a juan pablo guanipa.",
        "liberen a juan pablo guanipa y a todos los presos politicos sin excepcion",
        "ay tanto cuento, lo mismo de siempre, cambien el guión, ya aburren",
        "liberen a juan pablo guanipa ya!",
        "libertad para todos los secuestrados políticos! juan pablo guanipa libertad yá!",
        "liberen a juan pablo ya no es ningún delincuente",
        "creo que por ahí va la cosa, debe estar en malas condiciones de salud por eso no lo sacan. que desgraciados q son!!!",
        "que publiquen los videojuegos",
        "a juan pablo guanipa",
        "la pregunta es quien mató más venezolanos el bombardeó o 27 años de la dictadura",
        "ojo en el operativo de us, en caracas informan autoridades venezolanas q son más de 100 fallecidos de los cuales habían más de 60 militares cubanos y los presos políticos para cuando",
        "que pague su cana",
        "el está preso por ladrón no es preso politico",
        "para el régimen, juan pablo guanipa es una ficha de canje muy valiosa por eso la guarda para negociarla en el momento que le sea más conveniente",
        "¿seguro que no está en un burdel?",
        "ésto sé acabó, vienen por los que quedan",
        "y si armamos una campaña mundial, para liberar a américa de millones de delincuentes e inadaptados venezolanos y venezolanas que la cagan y recargan en los países a que han llegado. repudiados en el mundo",
        "que se quede dónde está. bien preso. la diarrea de mojón seco no mata a nadie.",
        "you have my respect.",
        "pedophiles are not deserving of nobel peace prizes! come on bill! don't pander like a little bitch now!",
        "how many countries does trump have to bomb before he gets the nobel peace prize?",
        "oh is that all? this guy got it for showing up.",
        "who's the guy who thinks it would be another iraq? he's uneducated on the culture and history of iran.",
        "at that point, in that case, awarding the nobel peace prize to trump would be more about lending credibility to the nobel prize itself than giving credit to trump.",
        "the real question is why did obama get the nobel peace prize",
        "this is the most insane take bill maher has ever had in a series of really insane takes. start three unnecessary wars, get god knows how many people killed, and win a peace price. zionist logic, i suppose.",
        "he should get the nobel prize anyway, but… iran, and cuba will fall! north korea will fall! so be it says the lord jesus christ!",
        "thanks for being our voice",
        "i guess you have a different idea of what the word \"peace\" means.",
        "yikes tell me you are with the epstein rapists with out telling me you are with the epstein rapists oh that’s right bill, you said woody allen was innocent you fucking loser",
        "don't fall for the perception management propaganda ...",
        "please help the people of iran",
        "yes but getting them to “fall” only matters as much as what comes next. topping a regime is one thing - putting it in a path toward peace and democracy is another.",
        "real peace is harder than pressure or leverage alone. it requires transitions that don’t simply replace one crisis with another. results matter more than rhetoric-and history tends to judge outcomes, not intentions.",
        "“peace” isn’t measured by how many regimes fall. it’s measured by how much human suffering is reduced.",
        "what does trump have on you?",
        "𝗜𝗙 𝗧𝗥𝗨𝗠𝗣 𝗙𝗟𝗜𝗣𝗦 𝗩𝗘𝗡𝗘𝗭𝗨𝗘𝗟𝗔, 𝗖𝗨𝗕𝗔, 𝗔𝗡𝗗 𝗜𝗥𝗔𝗡 𝗪𝗜𝗧𝗛𝗢𝗨𝗧 𝗔 𝗪𝗢𝗥𝗟𝗗 𝗪𝗔𝗥 — 𝗚𝗜𝗩𝗘 𝗛𝗜𝗠 𝗧𝗛𝗘 𝗡𝗢𝗕𝗘𝗟\u2063\u2063\u2063 maher basically did what most of the media refuses to do: step back and judge by 𝗼𝘂𝘁𝗰𝗼𝗺𝗲𝘀.\u2063\u2063\u2063 he’s looking at the",
        "not normally possible and hard to achieve at his age.. but bill maher actually became boring. congrats!",
        "thank you, bill, for supporting iranian people and for being our voice. the iranian people have been fighting for freedom and nothing can stop them. with the leadership of prince",
        "and true international support , this regime will finally fall. we won’t forget those",
        "lol the middle east is safer. lets see genocide in isreal, yeman is still being bombed, trump is building up an armada to bomb iran. al quada and isis in charge of syria. who the fuck are these shill kidding. it maybe safer for the people of afghanistan since we left.",
        "and here we are, watching another american wet dream of regime change dressed up as “peace.” trump “gets” venezuela, cuba, and iran to fall? that’s not peace that’s conquest by economic strangulation, color revolution, and proxy war, the same playbook that turned iraq into a",
        "trump's only effect in iran is that the people, the abused populous, know he supports them, instead of thinking the dictators are in league with the us admin. that's it, that's all you need to get them to rise up on their own, show unapologetic support.", "trump deserved it after all he's done so far.",
        "too unrealistic a dream, islamic factions in particular have fought to the death for centuries. w/judiah on the back burner next for their platter.",
        "all jews are like this.",
        "bill likes authoritarianism when it helps his tribe.",
        "thank you for your support!",
        "zionists a public enemy in america",
        ". we should treat all these mossad sock puppets the same way iran and north korea handle their mossad infestations.",
        "i completely disagree with the iraq comparison. the people of iraq were not as supportive in the removal of their leadership as the people in iran will be/are. if the us show no intention in occupying, i'd bet you would gain a valuable and unexpected ally.", "i'm surprised nobody has squared up on bill maher yet.", "maybe an apology from you would be just as valuable.",
        "what a jewish thing to say.",
        "you are a hitlerite zionist piece of shit. you are not funny and your hollywood peers hate you",
        "this is the first time i’ve seen you say something that was true! good on ya",
        "trump has to do three times as much as anyone else to get the nobel prize? who cares. you know what he gets if he does that? he gets to free millions of people in three countries from the horror of totalitarian socialism. that's what counts, not the silly, crooked prize.", "no he should not.",
        "how is war peace?",
        "spot on—bringing down iran's rotten regime is next after venezuela and cuba because it's crumbling from inside, protesters are torching the mullahs' lies. collapse is coming fast, trump just finish the job.", "kids will study this interview in the future and marvel at the stupidity that flowed through the airwaves",
        "if he helps iranians, all 80m of us will send email and will ask that the nobel piece prize to be given to him",
        "he hasn’t even gotten venezuela to fall lmfao. i guess if you call “removing one guy but keeping the same regime in power” falling. typical though to grade trump on a curve because if we didn’t he’d be a failure on every metric.",
        "he's kept the same venezuelan government in place, minus maduro. how does that help the people, can i ask?", "mientras no pueda poner tropas en territorio venezolano, es muy poco lo que puede hacer. y tiene chance hasta noviembre. ni siquiera puede levantar la producción petrolera.",
        "ha habido cosas muy buenas , otras … esperemos .",
        "si lo apoyo por su trabajo en venezuela",
        "serías el candidato ideal para la presidencia de venezuela",
        ". ya que tú serías el candidato de trump",
        "lo que el mundo pedía a gritos .. un líder.",
        "apoyo a tramp en todo",
        "fantástico. ¡ahora cuba y nicaragua!",
        "ahí se ponen duros con el scrache marduk. dales duro",
        "buenos días a trump",
        "me gusta pero más firmesa más mano dura ya",
        "si, claro el vio una oportunidad y la tomo y le dio a dos pájaros de un solo tiro. bien jugado",
        "de buena gana le daría un me gusta pero hay muchas cosas que en lo particular no estoy de acuerdo pienso que el trabajo aún está a medias",
        "el mejor presidente de usa",
        "ainda falta trabalho, a delci começou a mostrar as garrinhas de fora. tem que mandar um corretivo breve",
        "le queda muchísimo por hacer... el baila acaba de empezar!!",
        "vamos trump, hay que terminar con los comunistas...",
        "estaría estupendo que aplicará lo mismo que hizo en venezuela ahora en méxico",
        "no estoy de acuerdo my brother usted no sabes la consecuencia que trae ese tipo de acción un país se sale de control cuando hay un golpe de estado vas aver un mal manejo en ese país pana",
        "que se lleve lo que falta esa basura",
        "necesitamos políticos nvos en esa nva venezuela, estás basofias no deben tener cabida en una nación renacida, ojo que faltan varios allí!!",
        "en resunen, quedaste como la guayabera...",
        "¿qué pasó con las vértebras que tenías rota después de recibir el fulano premio? recomiendame ese traumatologo.",
        "ojalá y sea pronto bien pronto... porque el $ ya casi 370 ... la comida por las nubes igual los medicamentos ... la situación está muy dura...",
        "solo la fuerza y la mano firme de donald trump esta haciendo posible que todos los venezolanos recuperen su país,todavía falta sacar la cúpula militar chavista y sus protejidos como cabello,delcy,jorge,vladimir,colectivos y su jefe el señor cabello.",
        "mucha fuerza y ánimo querida",
        "hola maría dime para cuando y estaré ....",
        "maría corina urge la libertad de los presos y también el salario para poder comer algo , el hambre es muy grande y ya no se puede vivir",
        "yo digo que el que se presta, para peón del veneno es doble tonto y no quiero, ser bailarín de su fiesta... sr.",
        "todo tiene un tiempo bajo el sol y por ahora hay que esperar un tiempo seguro para su regreso dios sabra cual es.",
        "te dieron la espalda - y no llegaste a nada. eso te pasa por lambona justificando el genocidio en gaza.",
        "con la fé intacta hasta el final y la prosperidad de toda nuestra gente, todos unidos en una nación",
        "maría corina, mis respetos! se que tienes muy presente la condición salarial y de pensiones de nuestros trabajadores y viejitos, pero hago incapié en la necesidad de que se tomen cartas en el asunto lo mas pronto posible! venezuela toda te quiere, respeta y confía en ti",
        "mcm una gran lidereza, ejemplo a seguir, siempre fiel a sus principios y a pesar de sufrir persecucion jamas se doblego y su lucha x muchos años fue incansable, hasta llegar al punto de dar a conocer al mundo lo q sucedia en vnzla.pronto llegara la tan ansiada libertad",
        "gracias, gracias, ahora si estoy cerca de volver, ahora si voy a poder abrazar a mi familia siempre",
        "o por unos días o un mes, ahora si voy a ver a mi hijo crecer en familia y no solo conmigo y su papá. aquí estamos una familia lista para volver a nuestra tierra amada",
        "amén, ya quisiera regresar a mi patria, con una pensión que me permita vivir.",
        "te amo hoy y siempre. contigo leal hasta la eternidad.",
        "así mismo es guerrera de nuestro país venezuela",
        "gracias mcm. es urgente el aumento de los salarios y pensiones",
        "adiós condón que ya no sirves",
        "extraordinaria, dios te bendiga",
        "será repudiada...ya lo dijo, solo quiero vender los recursos petroleros de venezuela....y nada más",
        "lider que dificil camino no? cuidese la queremos de vuelta para gobernar",
        "te faltó decir: que viva la masonería!",
        "lo que se construye con la verdad es invencible. estamos contigo valiente líder porque tu coraje es el reflejo de nuestra nación. en venezuela te esperamos con la certeza de que la libertad y el reencuentro de nuestras familias están cerca",
        "te dieron una patada por el trasero y hasta el final era el 28 /01/ 2026 ..",
        "así será, así esta siendo con la fuerza, la fe y la esperanza de que vamos hasta el final. y con la casa limpia porq se trata de limpiar toda la podredumbre q se hizo en todos estos años. y construir algo nuevo con brillo propio. dios te proteja",
        "te amo maría corina",
        "amén y amén! señora m corina! un abrazo grande desde bogota colombia. un admirador!",
        # ... el resto de tu lista
    ]

    asyncio.run(procesar_sentimientos(comentarios_extraidos, 20, "Twitter"))
