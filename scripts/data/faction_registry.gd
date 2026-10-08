class_name FactionRegistry
extends RefCounted

## Registro central de facciones, independiente de la raza.
static func build_all() -> Dictionary:
	var factions := {}

	var dominion := Faction.new()
	dominion.id = "dominion"
	dominion.display_name = "El Dominio"
	dominion.synergy_threshold = 2
	dominion.group_bonus = {"defense_mult": 1.15}
	dominion.portrait_tags = ["gold", "order", "sacred_light"]
	factions[dominion.id] = dominion

	var outlaws := Faction.new()
	outlaws.id = "outlaws"
	outlaws.display_name = "Los Proscritos"
	outlaws.synergy_threshold = 2
	outlaws.group_bonus = {"crit_mult": 1.2}
	outlaws.portrait_tags = ["dark_cloak", "shadow", "rebel_marks"]
	factions[outlaws.id] = outlaws

	var abyss_cult := Faction.new()
	abyss_cult.id = "abyss_cult"
	abyss_cult.display_name = "El Culto del Abismo"
	abyss_cult.synergy_threshold = 2
	abyss_cult.group_bonus = {"magic_damage_mult": 1.3, "defense_mult": 0.85}
	abyss_cult.portrait_tags = ["void_purple", "runes", "abyss_eyes"]
	factions[abyss_cult.id] = abyss_cult

	var wanderers := Faction.new()
	wanderers.id = "wanderers"
	wanderers.display_name = "Los Errantes"
	wanderers.synergy_threshold = 3
	wanderers.group_bonus = {"loot_mult": 1.25}
	wanderers.portrait_tags = ["earth_tones", "nomad_gear", "clan_marks"]
	factions[wanderers.id] = wanderers

	return factions

## Devuelve el bonus de grupo activo (o {} si no hay suficiente sinergia),
## dado un array de ids de facción de los miembros del grupo actual.
static func resolve_group_bonus(faction_ids: Array[String], factions: Dictionary) -> Dictionary:
	var counts := {}
	for fid in faction_ids:
		counts[fid] = counts.get(fid, 0) + 1

	var best_bonus := {}
	for fid in counts.keys():
		var faction: Faction = factions.get(fid)
		if faction and counts[fid] >= faction.synergy_threshold:
			best_bonus = faction.group_bonus
	return best_bonus
