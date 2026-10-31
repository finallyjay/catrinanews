# Catrina News 💀🌼

**Las noticias tecnológicas del día, en calaveras literarias.** Un modelo abierto escribe en local versos satíricos sobre las empresas de los titulares de hoy, Python comprueba cada rima, y la Catrina los recita.

👉 **[catrinanews.tech](https://catrinanews.tech)** · [Read in English](README.md)

Hecho para el [Hacktoberfest Open-Source AI Challenge, Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26).

## La idea

Las calaveras literarias nacieron en la prensa satírica mexicana del siglo XIX para burlarse de los poderosos; las calaveras de José Guadalupe Posada, la Catrina entre ellas, salieron de esas páginas. Catrina News recupera ese origen: los poderosos de hoy son las tecnológicas.

## Cómo funciona

1. **Titulares** del motor de Google News de [SerpApi](https://serpapi.com) (España, últimas 24 horas, con el medio y el enlace real) junto al RSS de El País Tecnología. También funciona solo con RSS gratuitos, sin clave.
2. **El editor:** Gemma elige los titulares satirizables y les pone una categoría de una lista cerrada; el código deja uno por categoría y descarta cualquier titular sobre violencia, muertes o abusos, aunque el modelo lo elija.
3. **El poeta:** Gemma escribe la calavera y **[`rima.py`](rima.py), en Python puro, comprueba la rima consonante y cuenta las sílabas métricas** (tónica, diptongos, sinalefa). Si algo falla, le dice al modelo exactamente qué corregir.
4. **La traducción:** la rima no sobrevive a la traducción, así que el español es el original y el inglés es una traducción verso a verso.
5. **La voz:** ElevenLabs le pone voz a la Catrina.
6. **La hoja volante:** [`render.py`](render.py) la imprime al estilo Posada, en inglés o en español.

La IA se ejecuta una vez, en un portátil, como una imprenta; lo que se publica es HTML y MP3 estáticos.

## Lo que aprendí

- **La retroalimentación funciona; planificar, no.** Decirle al modelo qué sonidos fallaron subió la rima del 4B de 4/10 a 9/10. Pedirle que eligiera antes la pareja de rimas la bajó a 2/10, inventando palabras.
- **Cada regla que añadí, el modelo encontró la trampa.** *Panteón* → *millón* → otras palabras en *-ón*. Lo que funcionó fue prohibir *sonidos* de rima, algo que solo el código puede oír.
- **La forma es cosa del código; el sentido, del modelo.** Gemma 3 12B: 10/10 rimas, 34/40 versos de 7-9 sílabas.

Detalles, cifras y cómo ejecutarlo: [README en inglés](README.md).
