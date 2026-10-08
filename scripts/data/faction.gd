class_name Faction
extends Resource

## Identificador único de la facción (ej: "dominion", "outlaws")
@export var id: String = ""

## Nombre mostrado en UI
@export var display_name: String = ""

## Numero minimo de miembros del grupo con esta misma facción para que
## se active el bonus (ver group_bonus)
@export var synergy_threshold: int = 2

## Modificador aplicado al grupo entero cuando se alcanza synergy_threshold.
## Claves libres, resueltas por el sistema de combate (ej: "defense_mult": 1.15)
@export var group_bonus: Dictionary = {}

## Paleta/tags usados al componer el prompt del retrato de IA en el Ritual
@export var portrait_tags: Array[String] = []
