# detector-ia-tesis

Skill de Claude Code para detectar **señales** de redacción generada o asistida por IA en textos académicos en español (tesis, proyectos de tesis, capítulos, artículos). Solo detecta; nunca reescribe.

## Cómo analiza

Siete capas, cada una con evidencia citada del texto:

| Capa | Qué evalúa |
|---|---|
| A. Señales por categoría | 10 categorías puntuadas de 0 a 3: conectores de relleno, tríadas, vocabulario inflado o traducido, uniformidad de oraciones, transiciones mecánicas, inconsistencia terminológica, especificidad, atenuación, puntuación/formato y repetición semántica |
| B. Predictibilidad por párrafo | Cada párrafo aislado: ¿qué tan predecible es el resto a partir de su primera oración? |
| C. Consistencia de voz | Formalidad, persona gramatical, nivel léxico y ortografía a lo largo del texto (detecta textos mixtos) |
| D. Ritmo por oración | Variación de longitud, diversidad de inicios, brecha entre ritmo y contenido |
| E. Des-formalización | Residuos de texto generado y luego "humanizado": coloquialismos incongruentes, errores sembrados, estructura intacta |
| F. Fuentes y citas | Residuos de chatbot y referencias a verificar |
| G. Lectura holística y panel | Jurado de tesis, asesor/a, corrector/a de estilo y editor/a de revista |

El resultado es una **concentración de señales baja / moderada / alta** con un **nivel de confianza**, respaldada por:

- **Puntuación por categorías (0–30)** y escala detallada de 5 niveles (de ai-check).
- **Índice ponderado de capas (0–3)** con margen según la longitud (pesos de LAOUUUUU).
- **Puntos de patrón**: vocabulario por niveles y patrones estructurales (limpio → abrumador).
- **Extensión de la posible asistencia**: cuántos párrafos concentran señales.
- **Parecido tentativo con familias de modelos** (ChatGPT, Claude, Gemini).
- **Puntos a revisar**: dónde se concentran las señales y qué verificar, sin reescribir nada.

Ninguna cifra es un porcentaje de probabilidad: son sumas transparentes de observaciones citadas.

Inspirada en la lógica de [harshaneel/humanize](https://github.com/harshaneel/humanize) (`ai-check`) y [LAOUUUUU/Ai-detector-Claude-skill-](https://github.com/LAOUUUUU/Ai-detector-Claude-skill-), reescrita y adaptada al español académico.

## Estructura

```
detector-ia-tesis/
├── SKILL.md                 instrucciones de la skill
├── scripts/metricas.py      métricas objetivas (Python 3, sin dependencias)
└── references/lexico-es.md  catálogo de conectores, vocabulario, calcos y patrones
```

## Instalación

```bash
git clone https://github.com/<tu-usuario>/skills-ia-detector.git
mkdir -p ~/.claude/skills
cp -r skills-ia-detector/detector-ia-tesis ~/.claude/skills/
```

En Windows (PowerShell):

```powershell
git clone https://github.com/<tu-usuario>/skills-ia-detector.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse skills-ia-detector\detector-ia-tesis "$HOME\.claude\skills\"
```

Resultado esperado: `~/.claude/skills/detector-ia-tesis/SKILL.md`.

## Uso

En Claude Code, pega el texto y escribe, por ejemplo:

- "detecta si esto es IA"
- "revisa si suena a IA"
- "audita este borrador"

El script también funciona por separado:

```bash
python ~/.claude/skills/detector-ia-tesis/scripts/metricas.py capitulo.txt
```

## Límites

- El resultado es un indicio orientativo, **no una prueba** de autoría.
- No acusa a personas; habla del texto.
- Requiere al menos ~150–200 palabras.
- Usa niveles cualitativos (baja / moderada / alta), nunca porcentajes.
- Los catálogos de detección provienen mayormente de investigación en inglés; en español la confianza alta exige textos largos y señales convergentes.
- Para decisiones de alto impacto recomienda revisión humana adicional.
