class_name Race
extends Resource

## Identificador único de la raza (ej: "varkyn", "undead", "orc")
@export var id: String = ""

## Nombre mostrado en UI
@export var display_name: String = ""

## Sesgo de stats base, aplicado sobre el valor que decide el grado E->SSS.
## No reemplaza el grado, lo modula: el grado fija la magnitud, la raza la forma.
@export var stat_bias: Dictionary = {
	"strength": 1.0,
	"agility": 1.0,
	"intelligence": 1.0,
	"vitality": 1.0,
}

## Lista de formas bestiales disponibles (solo relevante para Varkyn; vacío en el resto)
@export var beast_forms: Array[String] = []

## Rasgos especiales por id, resueltos por el sistema de combate
## (ej: "group_bonus_orc", "immune_poison", "immune_bleed", "area_on_first_hit")
@export var traits: Array[String] = []
