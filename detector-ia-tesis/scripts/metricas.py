#!/usr/bin/env python3
"""Métricas objetivas de estilo para la skill detector-ia-tesis.

Calcula indicadores medibles (ritmo de oraciones, diversidad de inicios,
densidad de conectores, vocabulario marcado, puntuación, residuos de copia)
para que el análisis cite cifras reales en lugar de estimaciones.

Uso:
    python metricas.py archivo.txt
    python metricas.py < archivo.txt

Solo usa la biblioteca estándar. Las cifras son insumos para el análisis,
no un veredicto: ninguna métrica por sí sola indica autoría.
"""

import re
import statistics
import sys
import unicodedata
from collections import Counter

# --- Léxicos -----------------------------------------------------------------

CONECTORES = [
    "además", "asimismo", "así mismo", "por otro lado", "por otra parte",
    "en este sentido", "en ese sentido", "cabe destacar", "cabe señalar",
    "cabe mencionar", "es importante señalar", "es importante destacar",
    "es importante mencionar", "es importante resaltar", "es fundamental",
    "en definitiva", "en resumen", "en síntesis", "en conclusión",
    "por consiguiente", "por lo tanto", "de esta manera", "de este modo",
    "de esta forma", "en este contexto", "en ese contexto", "no obstante",
    "adicionalmente", "igualmente", "del mismo modo", "de igual manera",
    "en última instancia", "finalmente", "en primer lugar", "en segundo lugar",
    "por último", "sin embargo", "en consecuencia", "a su vez", "en efecto",
    "dicho esto", "en otras palabras", "es decir", "cabe resaltar",
]

# Nivel 1: muy característicos de salida de modelo en español.
VOCAB_N1 = [
    "crucial", "fundamental", "panorama", "sinergia", "holístico", "holística",
    "transformador", "transformadora", "multifacético", "multifacética",
    "entramado", "tapiz", "piedra angular", "pilar fundamental",
    "papel crucial", "papel fundamental", "rol fundamental", "rol crucial",
    "juega un papel", "juega un rol", "desempeña un papel",
    "en el panorama actual", "en el mundo actual", "en la era actual",
    "en la actualidad", "hoy en día", "en un mundo cada vez",
    "profundizar en", "navegar", "sumergirse", "adentrarse",
    "un testimonio de", "una miríada de", "sin precedentes",
    "marca un antes y un después", "en constante evolución",
    "vertiginoso", "vertiginosa", "potenciar", "robusto", "robusta",
]
# Nivel 2: frecuentes en IA, pero también normales en prosa académica.
VOCAB_N2 = [
    "abordar", "aborda", "abordaje", "fomentar", "fomenta", "significativo",
    "significativa", "significativamente", "integral", "clave", "óptimo",
    "optimizar", "impulsar", "impulsa", "garantizar", "resaltar", "subrayar",
    "diversos", "diversas", "amplia gama", "variedad de", "enriquecer",
    "enriquecedor", "innovador", "innovadora", "dinámico", "dinámica",
    "paradigma", "aprovechar", "herramienta poderosa", "valioso", "valiosa",
    "contribuye", "contribuir", "permite", "facilita", "facilitar",
]

# Nivel 3: señales leves; casi siempre normales en academia.
VOCAB_N3 = [
    "relevante", "notable", "notablemente", "particularmente", "específicamente",
    "diversos aspectos", "en general", "en términos de", "en lo que respecta a",
    "respectivamente", "implementa", "demuestra", "representa", "posibilita",
    "se alinea con", "potencial", "emergente", "más amplio", "más profundo",
    "cuando se trata de", "dicho lo anterior",
]

PATRONES_ESTRUCTURA = [
    # (regex, descripción, puntos por aparición)
    (r",\s+(evidenciando|destacando|resaltando|subrayando|demostrando|reflejando|permitiendo|posibilitando)\b",
     "gerundio de análisis superficial", 2),
    (r"(?i)\b(se erige como|se posiciona como|funge como|se configura como|sirve como)\b",
     "evasión de la cópula", 2),
    (r"(?i)\bno (?:es|se trata) (?:solo|solamente|únicamente) de\b[^.]{0,120}\bsino\b|\bno solo\b[^.]{0,120}\bsino\b",
     "paralelismo negativo", 2),
    (r"(?i)(?:^|[.!?]\s+)(?:veamos|exploremos|analicemos|profundicemos|examinemos)\b",
     "señalización de tutorial", 2),
    (r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "emoji", 2),
]

COLOQUIALES = [
    "la verdad", "ojo", "básicamente", "o sea", "vamos a ver", "está claro",
    "ni más ni menos", "a fin de cuentas", "total que", "pues", "bueno,",
    "la cosa es", "obvio", "súper", "un montón", "tipo que", "digamos",
    "fíjate", "mira,", "así de simple", "y ya", "ni hablar", "sinceramente",
    "honestamente", "para ser sinceros", "la neta", "bacán", "chévere", "ya que nada",
]

RESIDUOS_COPIA = [
    (r"utm_source=chatgpt\.com", "enlace con utm_source=chatgpt.com"),
    (r"oaicite|contentReference", "marcador interno de citas de ChatGPT"),
    (r"\*\*[^*\n]+\*\*", "negritas en sintaxis Markdown (**texto**)"),
    (r"(?m)^#{1,4} ", "encabezado en sintaxis Markdown (#)"),
    (r"(?i)como (un )?modelo de lenguaje", "frase de autopresentación de IA"),
    (r"(?i)\b(aquí tienes|claro,? aquí|¡claro!|espero que (esto|te) )",
     "fórmula conversacional de chatbot"),
    (r"\[(insertar|inserte|nombre|dato|autor|año)[^\]]*\]", "marcador de plantilla sin rellenar"),
]

ABREVIATURAS = [
    "p. ej.", "et al.", "etc.", "pp.", "p.", "vol.", "núm.", "n.º", "N.°",
    "cf.", "fig.", "Fig.", "Dr.", "Dra.", "Sr.", "Sra.", "ed.", "eds.",
    "cap.", "art.", "inc.", "Ud.", "Uds.", "aprox.", "op. cit.", "ibíd.",
    "I.E.", "S.A.", "EE. UU.", "N.º", "Nro.", "Av.", "Jr.", "Lic.", "Mg.", "Ing.",
]

# --- Utilidades --------------------------------------------------------------


def normalizar(texto):
    return unicodedata.normalize("NFC", texto)


def palabras(texto):
    return re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+(?:[-'][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*", texto)


def parrafos(texto):
    bloques = [b.strip() for b in re.split(r"\n\s*\n", texto)]
    return [b for b in bloques if len(palabras(b)) >= 15]


def oraciones(texto):
    protegido = texto
    for i, abr in enumerate(ABREVIATURAS):
        protegido = protegido.replace(abr, abr.replace(".", f"§{i}§"))
    partes = re.split(r"(?<=[.!?…])\s+(?=[¿¡«\"“(]?[A-ZÁÉÍÓÚÑ0-9])", protegido)
    resultado = []
    for parte in partes:
        for i, abr in enumerate(ABREVIATURAS):
            parte = parte.replace(f"§{i}§", ".")
        parte = parte.strip()
        if len(palabras(parte)) >= 3:
            resultado.append(parte)
    return resultado


def contar(texto_min, terminos):
    """Cuenta términos priorizando los más largos, para no contar dos veces
    «crucial» dentro de «papel crucial»."""
    hits = Counter()
    for t in sorted(terminos, key=len, reverse=True):
        patron = r"(?<![\wáéíóúñü])" + re.escape(t) + r"(?![\wáéíóúñü])"
        n = len(re.findall(patron, texto_min))
        if n:
            hits[t] = n
            texto_min = re.sub(patron, " ", texto_min)
    return hits


def por_mil(n, total):
    return round(n * 1000 / total, 1) if total else 0.0


def primera_palabra(oracion):
    ps = palabras(oracion)
    return ps[0].lower() if ps else ""


def inicia_con_conector(texto):
    inicio = texto.lower().lstrip("¿¡«\"“( ")[:40]
    for c in sorted(CONECTORES, key=len, reverse=True):
        if inicio.startswith(c):
            return c
    return None


def rachas_uniformes(longitudes, tolerancia=5, minimo=3):
    """Cuenta rachas de >= `minimo` oraciones consecutivas con longitudes a ±tolerancia."""
    rachas, actual = 0, 1
    for a, b in zip(longitudes, longitudes[1:]):
        if abs(a - b) <= tolerancia:
            actual += 1
        else:
            if actual >= minimo:
                rachas += 1
            actual = 1
    if actual >= minimo:
        rachas += 1
    return rachas


def mattr(tokens, ventana=100):
    """Moving-average type-token ratio: diversidad léxica estable ante la longitud."""
    if len(tokens) < ventana:
        return round(len(set(tokens)) / len(tokens), 3) if tokens else 0.0
    ratios = [len(set(tokens[i:i + ventana])) / ventana for i in range(len(tokens) - ventana + 1)]
    return round(statistics.mean(ratios), 3)


def fmt_hits(hits, maximo=12):
    if not hits:
        return "ninguno"
    return ", ".join(f"«{k}» ×{v}" for k, v in hits.most_common(maximo))


# --- Informe -----------------------------------------------------------------


def analizar(texto):
    texto = normalizar(texto)
    tmin = texto.lower()
    toks = [p.lower() for p in palabras(texto)]
    n_pal = len(toks)
    ors = oraciones(texto)
    longs = [len(palabras(o)) for o in ors]
    pars = parrafos(texto)

    out = []
    w = out.append
    w("# Métricas objetivas del texto\n")
    w("_Insumos cuantitativos para el análisis. Ninguna cifra es un veredicto._\n")

    w("## Muestra")
    w(f"- Palabras: {n_pal}")
    w(f"- Oraciones detectadas: {len(ors)}")
    w(f"- Párrafos (≥15 palabras): {len(pars)}")
    if n_pal < 150:
        w("- **Aviso:** muestra menor a 150 palabras; insuficiente para un veredicto.")
    elif n_pal < 400:
        w("- **Aviso:** muestra corta; la confianza del análisis debe limitarse a baja o media.")
    w("")

    if len(longs) >= 2:
        de = statistics.pstdev(longs)
        w("## Ritmo de oraciones (ráfaga)")
        w(f"- Longitud media: {statistics.mean(longs):.1f} palabras")
        w(f"- Desviación estándar: {de:.1f}  (referencia: >8 variado · 5–8 intermedio · 3–5 uniforme · <3 muy uniforme)")
        w(f"- Mínima / máxima: {min(longs)} / {max(longs)}")
        w(f"- Oraciones de menos de 8 palabras: {sum(1 for l in longs if l < 8)}")
        w(f"- Rachas de ≥3 oraciones consecutivas con longitud a ±5 palabras: {rachas_uniformes(longs)}")
        w(f"- Secuencia de longitudes: {longs[:60]}{' …' if len(longs) > 60 else ''}")
        w("")

        inicios = [primera_palabra(o) for o in ors]
        div = len(set(inicios)) / len(inicios)
        w("## Diversidad de inicios de oración")
        w(f"- Inicios únicos / total: {len(set(inicios))}/{len(inicios)} = {div:.0%}  (referencia: >70 % variado · 50–70 % intermedio · <50 % repetitivo)")
        w(f"- Más repetidos: {', '.join(f'«{k}» ×{v}' for k, v in Counter(inicios).most_common(6))}")
        w("")

    con = contar(tmin, CONECTORES)
    pars_con = [inicia_con_conector(p) for p in pars]
    w("## Conectores")
    w(f"- Total: {sum(con.values())} ({por_mil(sum(con.values()), n_pal)} por cada 1000 palabras)")
    w(f"- Detalle: {fmt_hits(con)}")
    if pars:
        n = sum(1 for c in pars_con if c)
        w(f"- Párrafos que empiezan con conector: {n}/{len(pars)}")
    w("")

    n1, n2, n3 = contar(tmin, VOCAB_N1), contar(tmin, VOCAB_N2), contar(tmin, VOCAB_N3)
    w("## Vocabulario marcado")
    w(f"- Nivel 1 (muy característico): {sum(n1.values())} ({por_mil(sum(n1.values()), n_pal)}/1000) — {fmt_hits(n1)}")
    w(f"- Nivel 2 (frecuente, también normal en academia): {sum(n2.values())} ({por_mil(sum(n2.values()), n_pal)}/1000) — {fmt_hits(n2)}")
    w(f"- Nivel 3 (leve, normal en academia): {sum(n3.values())} ({por_mil(sum(n3.values()), n_pal)}/1000) — {fmt_hits(n3)}")
    w(f"- Diversidad léxica (MATTR, ventana 100): {mattr(toks)}")
    w("")

    triadas = re.findall(
        r"\b[\wáéíóúñ]+(?: [\wáéíóúñ]+)?, [\wáéíóúñ]+(?: [\wáéíóúñ]+)?,? (?:y|e|o|u) [\wáéíóúñ]+(?: [\wáéíóúñ]+)?",
        texto,
    )
    w("## Enumeraciones ternarias candidatas")
    w(f"- Coincidencias del patrón «A, B y C»: {len(triadas)} ({por_mil(len(triadas), n_pal)}/1000)")
    for t in triadas[:10]:
        w(f"  - «{t}»")
    w("_Verificar a mano: el patrón también captura listas legítimas._\n")

    rayas = texto.count("—")
    rayas_esp = len(re.findall(r"\s—\s", texto))
    w("## Puntuación")
    w(f"- Rayas (—): {rayas} ({por_mil(rayas, n_pal)}/1000); con espacios a ambos lados (estilo inglés): {rayas_esp}")
    w(f"- Punto y coma: {texto.count(';')} ({por_mil(texto.count(';'), n_pal)}/1000)")
    w(f"- Dos puntos: {texto.count(':')} ({por_mil(texto.count(':'), n_pal)}/1000)")
    w(f"- Comillas latinas «»: {texto.count('«')} · inglesas “”/\"\": {texto.count('“') + texto.count(chr(34)) // 2}")
    w("")

    col = contar(tmin, COLOQUIALES)
    w("## Coloquialismos")
    w(f"- Total: {sum(col.values())} — {fmt_hits(col)}")
    w("")

    residuos = []
    for patron, desc in RESIDUOS_COPIA:
        m = re.findall(patron, texto)
        if m:
            residuos.append(f"{desc} ×{len(m)}")
    w("## Residuos de copia desde chatbot")
    w("- " + ("; ".join(residuos) if residuos else "ninguno"))
    w("")

    # Puntos de patrón (sección 3.1 de SKILL.md). Solo los patrones detectables
    # automáticamente; el resto (repetición semántica, simetría entre secciones,
    # perfección, apertura genérica, ausencia de opinión) los añade el análisis.
    filas = []
    pv = 3 * sum(n1.values()) + 2 * sum(n2.values()) + sum(n3.values())
    filas.append(("vocabulario (niv. 1×3, 2×2, 3×1)", "", pv))
    for patron, desc, pts in PATRONES_ESTRUCTURA:
        n = len(re.findall(patron, texto))
        if n:
            filas.append((desc, n, n * pts))
    if len(triadas) >= 3:
        filas.append(("tríadas reiteradas (≥3 candidatas)", len(triadas), 3))
    if len(pars) >= 3:
        lp0 = [len(palabras(p)) for p in pars]
        if statistics.pstdev(lp0) / statistics.mean(lp0) < 0.20:
            filas.append(("párrafos de longitud uniforme", "", 3))
    if rayas_esp >= 3 or (n_pal and rayas * 60 > n_pal and rayas >= 2):
        filas.append(("densidad de rayas a la inglesa", rayas, 3))
    total = sum(f[2] for f in filas)
    abrumador = bool(residuos)
    if abrumador:
        banda = "abrumador (residuo técnico de chatbot)"
    elif total <= 5:
        banda = "limpio"
    elif total <= 12:
        banda = "leve"
    elif total <= 22:
        banda = "moderado"
    elif total <= 35:
        banda = "fuerte"
    else:
        banda = "abrumador"
    w("## Puntos de patrón (automáticos, sin descuentos por género)")
    for desc, n, pts in filas:
        w(f"- {desc}{f' ×{n}' if n != '' else ''}: {pts} pts")
    w(f"- **Subtotal automático: {total} pts → {banda}**")
    w("_Faltan los patrones que requieren lectura (repetición semántica, simetría entre secciones, perfección, apertura genérica, ausencia de opinión, conclusión que reformula) y los descuentos por género._\n")

    if pars:
        lp = [len(palabras(p)) for p in pars]
        w("## Por párrafo")
        if len(lp) >= 2:
            cv = statistics.pstdev(lp) / statistics.mean(lp)
            w(f"- Coeficiente de variación de longitud de párrafo: {cv:.2f}  (valores <0.20 indican párrafos muy parejos)")
        w("")
        w("| # | Inicio | Palabras | Oraciones | DE long. oración | Conector inicial | Coloquialismos |")
        w("|---|---|---|---|---|---|---|")
        for i, p in enumerate(pars, 1):
            po = oraciones(p)
            pl = [len(palabras(o)) for o in po]
            de = f"{statistics.pstdev(pl):.1f}" if len(pl) >= 2 else "—"
            inicio = " ".join(palabras(p)[:5])
            colp = contar(p.lower(), COLOQUIALES)
            w(f"| P{i} | «{inicio}…» | {len(palabras(p))} | {len(po)} | {de} | {pars_con[i - 1] or '—'} | {fmt_hits(colp, 3)} |")
        w("")

    return "\n".join(out)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            texto = f.read()
    else:
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
        texto = sys.stdin.read()
    if not texto.strip():
        sys.exit("No se recibió texto.")
    print(analizar(texto))


if __name__ == "__main__":
    main()
