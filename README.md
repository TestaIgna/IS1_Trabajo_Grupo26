# \# 📌 Trabajo Integrador — Ingeniería de Software 1 (Grupo 26)

# 

# Repositorio correspondiente al Trabajo Práctico Integrador de la asignatura \*\*Ingeniería de Software 1\*\* de la \*\*Licenciatura en Ciencias de la Computación\*\* en la \*\*Universidad Nacional de Río Cuarto (UNRC)\*\*.

# 

# > \[!NOTE]

# > \*Corregí el apellido de "Herera" a "Herrera" guiándome por el usuario de GitHub del commit (`MileHerrera`). Si lleva una sola "r", ajústalo antes de hacer el push.\*

# 

# \---

# 

# \## 👥 Integrantes del Equipo

# 

# \* \*\*Ghersinich, Matías Ezequiel\*\*

# \* \*\*González, Alexsandra\*\*

# \* \*\*Gutiérrez, Brisa Valentina\*\*

# \* \*\*Herrera, Milena\*\*

# \* \*\*Testa, Ignacio Agustín\*\*

# 

# \---

# 

# \## 📐 Arquitectura y Diseño

# 

# El diseño del dominio modela una plataforma de preguntas y respuestas con sistema de votación, categorización mediante etiquetas y generación automatizada de respuestas a través de distintos proveedores de modelos de lenguaje (LLMs).

# 

# \### Patrones de Diseño Aplicados

# \* \*\*Strategy:\*\* Define una familia de algoritmos intercambiables (`ConcreteStrategyGemini`, `ConcreteLocal`, `ConcreteStrategyOpenAI`) a través de la interfaz `Strategy` para la generación de respuestas mediante IA.

# \* \*\*Factory Method:\*\* Desacopla la creación de las instancias de autores (`Usuario` y `RtaAutorLLM`) mediante la jerarquía `AutorFactory` y `AutorFabricaConcreta`.

# 

# \---

# 

# \## 📊 Diagrama de Clases (Mermaid)

# 

# ```mermaid

# classDiagram

# &#x20;   class Categoria {

# &#x20;       -nombre: string

# &#x20;   }

# 

# &#x20;   class Pregunta {

# &#x20;       -titulo: string

# &#x20;       -fecha\_p: date

# &#x20;       -cuerpo: string

# &#x20;   }

# 

# &#x20;   class Tag {

# &#x20;       -id: string

# &#x20;       -estilo: string

# &#x20;       -titulo: string

# &#x20;   }

# 

# &#x20;   class Votacion {

# &#x20;       -voto: TipoVoto

# &#x20;       +CalcularPuntuacion() void

# &#x20;   }

# &#x20;   note for Votacion "votacion no puede estar conectado a una pregunta y a una respuesta al mismo tiempo {XOR}"

# 

# &#x20;   class Respuesta {

# &#x20;       -fecha\_Publicacion: date

# &#x20;       -esAceptada: boolean

# &#x20;       -cuerpo: string

# &#x20;   }

# 

# &#x20;   class AutorRespuesta {

# &#x20;       <<abstract>>

# &#x20;       -nombre: string

# &#x20;       -rol: TipoRol

# &#x20;       +GetNombre() string

# &#x20;       +GetTipoRol() TipoRol

# &#x20;   }

# 

# &#x20;   class RtaAutorLLM {

# &#x20;       +GetNombre() string

# &#x20;       +GetTipoRol() TipoRol

# &#x20;       +responderPregunta(p: Pregunta) Respuesta

# &#x20;   }

# 

# &#x20;   class Usuario {

# &#x20;       -email: string

# &#x20;       -contraseña: string

# &#x20;       +GetNombre() string

# &#x20;       +GetTipoRol() TipoRol

# &#x20;   }

# 

# &#x20;   class AutorFactory {

# &#x20;       <<abstract>>

# &#x20;       +crearAutor() AutorRespuesta

# &#x20;   }

# 

# &#x20;   class AutorFabricaConcreta {

# &#x20;       +crearAutor() AutorRespuesta

# &#x20;   }

# 

# &#x20;   class Strategy {

# &#x20;       <<interface>>

# &#x20;       +generarRespuesta(titulo: string, cuerpo: string) string

# &#x20;   }

# 

# &#x20;   class ConcreteStrategyGemini {

# &#x20;       +generarRespuesta(titulo: string, cuerpo: string) string

# &#x20;   }

# 

# &#x20;   class ConcreteLocal {

# &#x20;       +generarRespuesta(titulo: string, cuerpo: string) string

# &#x20;   }

# 

# &#x20;   class ConcreteStrategyOpenAI {

# &#x20;       +generarRespuesta(titulo: string, cuerpo: string) string

# &#x20;   }

# 

# &#x20;   class TipoVoto {

# &#x20;       <<enumeration>>

# &#x20;       POSITIVO

# &#x20;       NEGATIVO

# &#x20;   }

# 

# &#x20;   class TipoRol {

# &#x20;       <<enumeration>>

# &#x20;       USERGRAL

# &#x20;       ADMIN

# &#x20;       BOT

# &#x20;   }

# 

# &#x20;   %% Relaciones de Dominio

# &#x20;   Categoria "1" <-- "\*" Pregunta : -asociada

# &#x20;   Pregunta "\*" -- "\*" Tag

# &#x20;   Pregunta "1" <-- "\*" Respuesta

# &#x20;   

# &#x20;   Votacion "\*" --> "0..1" Pregunta

# &#x20;   Votacion "\*" --> "0..1" Respuesta

# &#x20;   Votacion "\*" --> "1" Usuario

# 

# &#x20;   Respuesta "\*" --> "1" AutorRespuesta

# 

# &#x20;   %% Herencia de Autores

# &#x20;   AutorRespuesta <|-- RtaAutorLLM

# &#x20;   AutorRespuesta <|-- Usuario

# 

# &#x20;   %% Patrón Factory

# &#x20;   AutorFactory <|-- AutorFabricaConcreta

# &#x20;   AutorFabricaConcreta ..> RtaAutorLLM

# &#x20;   AutorFabricaConcreta ..> Usuario

# 

# &#x20;   %% Patrón Strategy

# &#x20;   RtaAutorLLM "1" --> "1" Strategy

# &#x20;   Strategy <|.. ConcreteStrategyGemini

# &#x20;   Strategy <|.. ConcreteLocal

# &#x20;   Strategy <|.. ConcreteStrategyOpenAI

# ```



classDiagram

&#x20;   class Tag {

&#x20;       -id: string

&#x20;       -estilo: string

&#x20;       -titulo: string

&#x20;   }



&#x20;   class Respuesta {

&#x20;       -fecha\_Publicacion: date

&#x20;       -esAceptada: boolean

&#x20;       -cuerpo: string

&#x20;   }



&#x20;   class AutorRespuesta {

&#x20;       <<abstract>>

&#x20;       -nombre: string

&#x20;       -rol: TipoRol

&#x20;       +GetNombre() string

&#x20;       +GetTipoRol() TipoRol

&#x20;   }



&#x20;   class RtaAutorLLM {

&#x20;       +GetNombre() string

&#x20;       +GetTipoRol() TipoRol

&#x20;       +responderPregunta(p: Pregunta) Respuesta

&#x20;   }



&#x20;   class Usuario {

&#x20;       -email: string

&#x20;       -contraseña: string

&#x20;       +GetNombre() string

&#x20;       +GetTipoRol() TipoRol

&#x20;   }



&#x20;   class AutorFabricaConcreta {

&#x20;       +crearAutor() AutorRespuesta

&#x20;   }



&#x20;   class Strategy {

&#x20;       <<interface>>

&#x20;       +generarRespuesta(titulo: string, cuerpo: string) string

&#x20;   }



&#x20;   class ConcreteStrategyGemini {

&#x20;       +generarRespuesta(titulo: string, cuerpo: string) string

&#x20;   }



&#x20;   class ConcreteLocal {

&#x20;       +generarRespuesta(titulo: string, cuerpo: string) string

&#x20;   }



&#x20;   class ConcreteStrategyOpenAI {

&#x20;       +generarRespuesta(titulo: string, cuerpo: string) string

&#x20;   }



&#x20;   class TipoVoto {

&#x20;       <<enumeration>>

&#x20;       POSITIVO

&#x20;       NEGATIVO

&#x20;   }



&#x20;   class TipoRol {

&#x20;       <<enumeration>>

&#x20;       USERGRAL

&#x20;       ADMIN

&#x20;       BOT

&#x20;   }



&#x20;   %% Relaciones visibles en el corte actual

&#x20;   Respuesta "\*" --> "1" AutorRespuesta

&#x20;   AutorRespuesta <|-- RtaAutorLLM

&#x20;   AutorRespuesta <|-- Usuario



&#x20;   RtaAutorLLM "1" --> "1" Strategy



&#x20;   Strategy <|.. ConcreteStrategyGemini

&#x20;   Strategy <|.. ConcreteLocal

&#x20;   Strategy <|.. ConcreteStrategyOpenAI



&#x20;   AutorFabricaConcreta ..> RtaAutorLLM

&#x20;   AutorFabricaConcreta ..> Usuario

