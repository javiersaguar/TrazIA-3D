"""Estrategia C · RAG (DEC-08): biblioteca de equipos aprobados, recuperación y plantilla.

- `fingerprint`: huella de página (densidad de tinta en rejilla + vocabulario) para recuperar el
  GA más parecido, sea vectorial o escaneado.
- `library`: construye y carga la biblioteca: por equipo aprobado, su huella y la plantilla de
  lectura (región de cada campo verificado).

Regla fija: un valor recuperado nunca entra sin evidencia del documento actual. De la biblioteca
solo se hereda dónde mirar; el valor se lee en el documento que se procesa.
"""
