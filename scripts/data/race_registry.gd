class_name RaceRegistry
extends RefCounted

## Registro central de razas. Crea los Race.new() en código para evitar tener
## que fabricar .tres a mano; conviertelo a recursos .tres desde el editor si
## prefieres esa flexibilidad luego.
static func build_all() -> Dictionary:
	var races := {}

	var varkyn := Race.new()
	varkyn.id = "varkyn"
	varkyn.display_name = "Varkyn"
	varkyn.stat_bias = {"strength": 1.05, "agility": 1.2, "intelligence": 0.9, "vitality": 1.0}
	varkyn.beast_forms = ["wolf", "fox", "bear", "boar", "eagle", "snake", "lynx", "raven"]
	varkyn.traits = []
	races[varkyn.id] = varkyn

	var undead := Race.new()
	undead.id = "undead"
	undead.display_name = "Undead"
	undead.stat_bias = {"strength": 1.1, "agility": 0.85, "intelligence": 1.0, "vitality": 1.25}
	undead.traits = ["immune_poison", "immune_bleed", "weak_holy"]
	races[undead.id] = undead

	var demon := Race.new()
	demon.id = "demon"
	demon.display_name = "Demonio"
	demon.stat_bias = {"strength": 0.9, "agility": 1.0, "intelligence": 1.3, "vitality": 0.85}
	demon.traits = ["elemental_damage_bonus"]
	races[demon.id] = demon

	var orc := Race.new()
	orc.id = "orc"
	orc.display_name = "Orco"
	orc.stat_bias = {"strength": 1.3, "agility": 0.9, "intelligence": 0.8, "vitality": 1.15}
	orc.traits = ["group_bonus_orc"]
	races[orc.id] = orc

	var goblin := Race.new()
	goblin.id = "goblin"
	goblin.display_name = "Goblin"
	goblin.stat_bias = {"strength": 0.75, "agility": 1.3, "intelligence": 1.05, "vitality": 0.7}
	goblin.traits = ["loot_bonus", "crit_bonus"]
	races[goblin.id] = goblin

	var minotaur := Race.new()
	minotaur.id = "minotaur"
	minotaur.display_name = "Minotauro"
	minotaur.stat_bias = {"strength": 1.35, "agility": 0.75, "intelligence": 0.75, "vitality": 1.2}
	minotaur.traits = ["area_on_first_hit"]
	races[minotaur.id] = minotaur

	return races
