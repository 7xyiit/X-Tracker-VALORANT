import time
import requests
from .colors import Colors
from .cache import cache

def get_recent_matches(puuid, shard, headers, queue="competitive", max_matches=5):
    """Son maçların ID'lerini al"""
    try:
        # Rate limit için bekle
        time.sleep(2)  # 2 saniye bekle
        
        response = requests.get(
            f'https://pd.{shard}.a.pvp.net/mmr/v1/players/{puuid}/competitiveupdates?startIndex=0&endIndex={max_matches}&queue={queue}',
            headers=headers,
            verify=False
        )
        
        if response.status_code == 200:
            matches = response.json().get("Matches", [])
            return [match.get("MatchID") for match in matches if match.get("MatchID")]
        return []
        
    except Exception as e:
        print(f"Son maçlar alınamadı ({queue}): {e}")
        return []

def get_all_recent_matches(puuid, shard, headers, max_matches=5):
    """Tüm son maçların ID'lerini al (competitive ve unrated dahil)"""
    try:
        # Rate limit için bekle
        time.sleep(1)
        
        # Önce competitive maçları dene
        response = requests.get(
            f'https://pd.{shard}.a.pvp.net/mmr/v1/players/{puuid}/competitiveupdates?startIndex=0&endIndex={max_matches}',
            headers=headers,
            verify=False
        )
        
        if response.status_code == 200:
            matches = response.json().get("Matches", [])
            return [match.get("MatchID") for match in matches if match.get("MatchID")]
        return []
        
    except Exception as e:
        print(f"Tüm maçlar alınamadı: {e}")
        return []

def get_headshot_percentage(puuid, shard, headers):
    # Önce cache'e bak
    cached_data = cache.get('hs_stats', puuid)
    if cached_data:
        return cached_data
        
    try:
        total_hits = 0
        total_headshots = 0
        processed_matches = 0
        
        # Önce competitive maçları dene
        match_ids = get_recent_matches(puuid, shard, headers, "competitive", 5)
        
        # Eğer competitive maç yoksa, tüm maçları al
        if not match_ids:
            match_ids = get_all_recent_matches(puuid, shard, headers, 5)
        
        if not match_ids:
            return "?"
            
        # En fazla 3 maç kontrol et
        for match_id in match_ids[:3]:
            if processed_matches >= 3:
                break
                
            try:
                # Rate limit için bekle
                time.sleep(0.5)
                
                # Maç detaylarını al
                response = requests.get(
                    f'https://pd.{shard}.a.pvp.net/match-details/v1/matches/{match_id}',
                    headers=headers,
                    verify=False
                )
                
                if response.status_code != 200:
                    continue
                    
                match_data = response.json()
                processed_matches += 1
                
                # Her round için damage verilerini topla
                for round_result in match_data.get("roundResults", []):
                    for player_stats in round_result.get("playerStats", []):
                        if player_stats.get("subject") == puuid:
                            damage_stats = player_stats.get("damage", [])
                            
                            for damage in damage_stats:
                                total_hits += damage.get("legshots", 0) + damage.get("bodyshots", 0) + damage.get("headshots", 0)
                                total_headshots += damage.get("headshots", 0)
                
            except Exception as e:
                continue
        
        if total_hits > 0:
            hs_percentage = int((total_headshots / total_hits) * 100)
            
            # HS oranına göre renk seç
            if hs_percentage < 25:
                color = "\033[38;5;137m"  # Hafif kapalı kahverengi
            elif hs_percentage < 50:
                color = "\033[38;5;108m"  # Hafif kapalı yeşil
            else:
                color = "\033[38;5;120m"  # Açık yeşil
                
            result = f"{color}%{hs_percentage}{Colors.RESET}"
            
            # Sonucu cache'e kaydet
            cache.set('hs_stats', puuid, result)
            
            return result
        
        return "?"
    except Exception as e:
        return "?" 