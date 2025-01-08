import time
import requests
from .colors import Colors

def get_last_competitive_match(puuid, shard, headers):
    try:
        # Rate limit için bekle
        time.sleep(2)  # 2 saniye bekle
        
        response = requests.get(
            f'https://pd.{shard}.a.pvp.net/mmr/v1/players/{puuid}/competitiveupdates?startIndex=0&endIndex=1&queue=competitive',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        matches = response.json().get("Matches", [])
        if matches:
            return matches[0].get("MatchID")
        return None
    except Exception as e:
        print(f"Son rekabetçi maç bilgisi alınamadı: {e}")
        return None

def get_headshot_percentage(puuid, shard, headers):
    try:
        # Son rekabetçi maçı al
        match_id = get_last_competitive_match(puuid, shard, headers)
        if not match_id:
            return "?"
            
        # Maç detaylarını al
        response = requests.get(
            f'https://pd.{shard}.a.pvp.net/match-details/v1/matches/{match_id}',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        match_data = response.json()
        
        # Tüm roundlardaki toplam vuruşları hesapla
        total_hits = 0
        total_headshots = 0
        
        # Her round için damage verilerini topla
        for round_result in match_data.get("roundResults", []):
            for player_stats in round_result.get("playerStats", []):
                if player_stats.get("subject") == puuid:
                    damage_stats = player_stats.get("damage", [])
                    
                    for damage in damage_stats:
                        total_hits += damage.get("legshots", 0) + damage.get("bodyshots", 0) + damage.get("headshots", 0)
                        total_headshots += damage.get("headshots", 0)
        
        if total_hits > 0:
            hs_percentage = int((total_headshots / total_hits) * 100)
            
            # HS oranına göre renk seç
            if hs_percentage < 25:
                color = "\033[38;5;137m"  # Hafif kapalı kahverengi
            elif hs_percentage < 50:
                color = "\033[38;5;108m"  # Hafif kapalı yeşil
            else:
                color = "\033[38;5;120m"  # Açık yeşil
                
            return f"{color}%{hs_percentage}{Colors.RESET}"
        
        return "?"
    except Exception as e:
        return "?" 