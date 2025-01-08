from tabulate import tabulate
from .colors import Colors
from .api import get_vandal_skins, get_agent_names

def create_player_table(match_details, player_names, loadouts=None):
    headers = ["Parti", "Ajan", "Oyuncu", "Skin", "Rank", "Peak Rank", "HS%", "Seviye"]
    attackers_data = []
    defenders_data = []
    
    # Skin ve ajan isimlerini al
    vandal_skins = get_vandal_skins()
    agent_names = get_agent_names()
    
    # Loadout ve rank verilerini işle
    player_skins = {}
    player_agents = {}
    if loadouts:
        player_skins = loadouts.get("PlayerSkins", {})
        player_agents = loadouts.get("PlayerAgents", {})
        
    player_ranks = match_details.get("PlayerRanks", {})
    player_peak_ranks = match_details.get("PlayerPeakRanks", {})
    player_levels = match_details.get("PlayerLevels", {})
    player_hs_percentages = match_details.get("PlayerHSPercentages", {})
    player_parties = match_details.get("PlayerParties", {})
    
    for player in match_details.get("Players", []):
        player_puuid = player.get("Subject")
        player_name = "?"
        
        # Oyuncu ismini bul
        for name_data in player_names:
            if name_data.get("Subject") == player_puuid:
                player_name = f"{name_data.get('GameName', '?')}#{name_data.get('TagLine', '?')}"
                break
        
        # Ajan ismini bul
        agent_id = player_agents.get(player_puuid, "?")
        agent_name = agent_names.get(agent_id, "?")
        
        # Vandal skinini bul
        skin_id = player_skins.get(player_puuid, "?")
        vandal_skin = vandal_skins.get(skin_id, "?")
        
        # Rank bilgilerini al
        rank = player_ranks.get(player_puuid, "?")
        peak_rank = player_peak_ranks.get(player_puuid, "?")
        
        # Level bilgisini al
        level = player_levels.get(player_puuid, "?")
        
        # HS oranını al
        hs_percentage = player_hs_percentages.get(player_puuid, "?")
        
        # Parti durumunu kontrol et
        party_status = "P" if player_puuid in player_parties else " "
        
        # Oyuncu ismini renklendir
        colored_name = f"{Colors.BLUE}{player_name}{Colors.RESET}" if player.get("TeamID") == "Blue" else f"{Colors.RED}{player_name}{Colors.RESET}"
        
        player_data = [
            f"{Colors.RED}{party_status}{Colors.RESET}",  # Parti durumu
            agent_name,
            colored_name,
            vandal_skin,
            rank,
            peak_rank,
            hs_percentage,
            level
        ]
        
        # Takıma göre ayır
        if player.get("TeamID") == "Blue":
            defenders_data.append(player_data)
        else:
            attackers_data.append(player_data)
    
    # Takımları birleştir ve araya boşluk ekle
    table = "\n\n" + Colors.BLUE + "━━━ SAVUNAN TAKIM ━━━" + Colors.RESET + "\n"
    table += tabulate(defenders_data, headers=headers, tablefmt="heavy_grid")
    table += "\n\n" + Colors.RED + "━━━ SALDIRAN TAKIM ━━━" + Colors.RESET + "\n"
    table += tabulate(attackers_data, headers=headers, tablefmt="heavy_grid")
    
    return table 