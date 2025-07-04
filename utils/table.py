from .colors import Colors
from .api import get_vandal_skins, get_agent_names
import unicodedata
import re

def strip_ansi_codes(text):
    """ANSI renk kodlarını kaldır"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', str(text))

def truncate_text(text, max_length):
    """Metni belirtilen uzunlukta kes - renk kodlarını koru"""
    clean_text = strip_ansi_codes(text)
    if len(clean_text) > max_length:
        # Renk kodlarını tespit et
        color_start = ""
        color_end = ""
        
        # Başlangıçtaki renk kodunu bul
        color_match = re.search(r'^(\x1B\[[0-9;]*m)', text)
        if color_match:
            color_start = color_match.group(1)
        
        # Reset kodunu kontrol et
        if Colors.RESET in text:
            color_end = Colors.RESET
        
        # Metni kes
        truncated_clean = clean_text[:max_length-3] + "..."
        
        # Renk kodlarını geri ekle
        return color_start + truncated_clean + color_end
    return text

def pad_text(text, width, align='left'):
    """Metni belirtilen genişlikte hizala"""
    clean_text = strip_ansi_codes(text)
    padding_needed = max(0, width - len(clean_text))
    
    if align == 'center':
        left_pad = padding_needed // 2
        right_pad = padding_needed - left_pad
        return ' ' * left_pad + text + ' ' * right_pad
    elif align == 'right':
        return ' ' * padding_needed + text
    else:  # left
        return text + ' ' * padding_needed

def create_player_table(match_details, player_names, loadouts=None):
    # Sütun başlıkları ve genişlikleri (optimize edildi)
    columns = [
        ("P", 1),       # Parti
        ("Ajan", 15),    # Ajan (artırıldı)
        ("Oyuncu", 22),  # Oyuncu (artırıldı)
        ("Skin", 20),    # Skin
        ("Rank", 18),    # Rank (azaltıldı)
        ("Peak", 15),    # Peak Rank
        ("HS%", 6),      # HS% (artırıldı)
        ("WR", 12),      # WR (artırıldı)
        ("Lvl", 5)       # Seviye (3'ten 5'e artırıldı)
    ]
    
    total_width = sum(width for _, width in columns) + len(columns) - 1  # +1 for separators
    
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
    player_winrates = match_details.get("PlayerWinrates", {})
    player_parties = match_details.get("PlayerParties", {})
    
    for player in match_details.get("Players", []):
        player_puuid = player.get("Subject")
        player_name = "?"
        
        # Oyuncu ismini bul
        for name_data in player_names:
            if name_data.get("Subject") == player_puuid:
                player_name = f"{name_data.get('GameName', '?')}#{name_data.get('TagLine', '?')}"
                player_name = unicodedata.normalize('NFKC', player_name)
                break
        
        # Ajan ismini bul ve temizle
        agent_id = player_agents.get(player_puuid, "?")
        agent_name = agent_names.get(agent_id, "?")
        # Renk kodlarını koru
        
        # Vandal skinini bul
        skin_id = player_skins.get(player_puuid, "?")
        vandal_skin = vandal_skins.get(skin_id, "?")
        
        # Rank bilgilerini al
        rank = player_ranks.get(player_puuid, "?")
        peak_rank = player_peak_ranks.get(player_puuid, "?")
        
        # Level bilgisini al
        level = player_levels.get(player_puuid, "?")
        
        # Seviye kontrolü - gizli, 0 veya yoksa "?" göster
        if level == "Gizli":
            level = "GIZLI"  # 5 karakter tam uyuyor
        elif level == 0 or level == "?":
            level = "?"
        
        # HS oranını ve Winrate'i al
        hs_percentage = player_hs_percentages.get(player_puuid, "?")
        winrate = player_winrates.get(player_puuid, "?")
        
        # Parti durumunu kontrol et
        party_status = "P" if player_puuid in player_parties else ""
        
        # Oyuncu ismini renklendir
        team_color = Colors.BLUE if player.get("TeamID") == "Blue" else Colors.RED
        colored_name = f"{team_color}{player_name}{Colors.RESET}"
        
        # Veriyi sütun genişliklerine göre düzenle
        row_data = [
            truncate_text(party_status, columns[0][1]),
            truncate_text(agent_name, columns[1][1]),
            truncate_text(colored_name, columns[2][1]),
            truncate_text(vandal_skin, columns[3][1]),
            truncate_text(rank, columns[4][1]),
            truncate_text(peak_rank, columns[5][1]),
            truncate_text(str(hs_percentage), columns[6][1]),
            truncate_text(str(winrate), columns[7][1]),
            truncate_text(str(level), columns[8][1])
        ]
        
        # Takıma göre ayır
        if player.get("TeamID") == "Blue":
            defenders_data.append(row_data)
        else:
            attackers_data.append(row_data)
    
    # Tablo oluştur
    def create_table_section(title, data, title_color):
        if not data:
            return ""
            
        result = f"\n{title_color}{title}{Colors.RESET}\n"
        result += "─" * total_width + "\n"
        
        # Başlık satırı
        header_row = " ".join([
            pad_text(f"{Colors.BOLD}{header}{Colors.RESET}", width, 'center')
            for header, width in columns
        ])
        result += header_row + "\n"
        result += "─" * total_width + "\n"
        
        # Veri satırları
        for row in data:
            formatted_row = " ".join([
                pad_text(cell, columns[i][1], 'center')
                for i, cell in enumerate(row)
            ])
            result += formatted_row + "\n"
        
        result += "─" * total_width + "\n"
        return result
    
    # Tabloları birleştir
    table = create_table_section(
        "🛡️  SAVUNAN TAKIM", 
        defenders_data, 
        Colors.BLUE
    )
    
    table += create_table_section(
        "⚔️  SALDIRAN TAKIM", 
        attackers_data, 
        Colors.RED
    )
    
    return table 