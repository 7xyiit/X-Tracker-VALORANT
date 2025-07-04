from .colors import Colors
from .api import get_current_season_id
from .cache import cache
import requests

def get_rank_name(tier):
    rank_colors = {
        0: Colors.RESET, 1: Colors.RESET, 2: Colors.RESET,  # Unranked
        3: Colors.IRON, 4: Colors.IRON, 5: Colors.IRON,  # Iron
        6: Colors.BRONZE, 7: Colors.BRONZE, 8: Colors.BRONZE,  # Bronze
        9: Colors.SILVER, 10: Colors.SILVER, 11: Colors.SILVER,  # Silver
        12: Colors.GOLD, 13: Colors.GOLD, 14: Colors.GOLD,  # Gold
        15: Colors.PLATINUM, 16: Colors.PLATINUM, 17: Colors.PLATINUM,  # Platinum
        18: Colors.DIAMOND, 19: Colors.DIAMOND, 20: Colors.DIAMOND,  # Diamond
        21: Colors.ASCENDANT, 22: Colors.ASCENDANT, 23: Colors.ASCENDANT,  # Ascendant
        24: Colors.IMMORTAL, 25: Colors.IMMORTAL, 26: Colors.IMMORTAL,  # Immortal
        27: Colors.RADIANT  # Radiant
    }
    
    rank_names = {
        0: "Derecesiz", 1: "Derecesiz", 2: "Derecesiz",
        3: "Demir 1", 4: "Demir 2", 5: "Demir 3",
        6: "Bronz 1", 7: "Bronz 2", 8: "Bronz 3",
        9: "Gümüş 1", 10: "Gümüş 2", 11: "Gümüş 3",
        12: "Altın 1", 13: "Altın 2", 14: "Altın 3",
        15: "Platin 1", 16: "Platin 2", 17: "Platin 3",
        18: "Elmas 1", 19: "Elmas 2", 20: "Elmas 3",
        21: "Yücelik 1", 22: "Yücelik 2", 23: "Yücelik 3",
        24: "Ölümsüzlük 1", 25: "Ölümsüzlük 2", 26: "Ölümsüzlük 3",
        27: "Radyant"
    }
    
    rank_color = rank_colors.get(tier, Colors.RESET)
    rank_name = rank_names.get(tier, "?")
    
    return f"{rank_color}{rank_name}{Colors.RESET}"

def get_player_ranks(puuid, shard, headers):
    # Önce cache'e bak
    cached_data = cache.get('ranks', puuid)
    if cached_data:
        return cached_data
        
    try:
        response = requests.get(
            f'https://pd.{shard}.a.pvp.net/mmr/v1/players/{puuid}',
            headers=headers,
            verify=False
        )
        
        if response.status_code != 200:
            return "Derecesiz", "Derecesiz", "?"
        
        # JSON parse hatasını yakala
        try:
            rank_data = response.json()
        except (ValueError, TypeError) as json_error:
            print(f"JSON parse hatası: {json_error}")
            return "Derecesiz", "Derecesiz", "?"
            
        # Boş response kontrolleri
        if not rank_data or rank_data is None:
            return "Derecesiz", "Derecesiz", "?"
            
        if not isinstance(rank_data, dict):
            print(f"Beklenmeyen response format: {type(rank_data)}")
            return "Derecesiz", "Derecesiz", "?"
            
        # Güncel sezon ID'sini al
        current_season = get_current_season_id(shard, headers)
        if not current_season:
            return "Derecesiz", "Derecesiz", "?"
            
        # Güvenli veri erişimi
        queue_skills = rank_data.get("QueueSkills")
        if not queue_skills or not isinstance(queue_skills, dict):
            return "Derecesiz", "Derecesiz", "?"
            
        competitive = queue_skills.get("competitive")
        if not competitive or not isinstance(competitive, dict):
            return "Derecesiz", "Derecesiz", "?"
            
        seasonal_info = competitive.get("SeasonalInfoBySeasonID")
        if not seasonal_info or not isinstance(seasonal_info, dict):
            return "Derecesiz", "Derecesiz", "?"
        
        # Güncel rank bilgisini bul
        current_season_data = seasonal_info.get(current_season, {})
        
        # API dokümantasyonuna göre NumberOfWinsWithPlacements kullan (placement maçları dahil)
        current_wins_with_placements = current_season_data.get("NumberOfWinsWithPlacements", 0)
        current_wins = current_season_data.get("NumberOfWins", 0)  # Yedek olarak
        current_games = current_season_data.get("NumberOfGames", 0)
        
        # Önce NumberOfWinsWithPlacements kullan, yoksa NumberOfWins
        current_win_count = current_wins_with_placements if current_wins_with_placements > 0 else current_wins
        
        total_wins = current_win_count
        total_games = current_games
        
        # Eğer güncel sezonda yeterli oyun yoksa, son birkaç sezonu kontrol et
        if total_games < 3:  # Eğer 3'ten az oyun varsa diğer sezonları da dahil et
            for season_id, season_info in seasonal_info.items():
                if season_info and season_id != current_season:
                    # Önce NumberOfWinsWithPlacements, yoksa NumberOfWins
                    season_wins_with_placements = season_info.get("NumberOfWinsWithPlacements", 0)
                    season_wins = season_info.get("NumberOfWins", 0)
                    season_win_count = season_wins_with_placements if season_wins_with_placements > 0 else season_wins
                    
                    total_wins += season_win_count
                    total_games += season_info.get("NumberOfGames", 0)
        
        # Winrate hesapla ve renklendir
        winrate = "?"
        if total_games > 0:
            winrate_value = (total_wins / total_games) * 100
            
            # Winrate'e göre renk seç
            if winrate_value < 40:
                color = "\033[38;5;130m"  # Kahverengi
            elif winrate_value < 60:
                color = "\033[38;5;214m"  # Turuncu
            else:
                color = "\033[38;5;28m"   # Yeşil
                
            winrate = f"{color}%{int(winrate_value)}{Colors.RESET} ({total_games})"
        
        # Güncel sezon rankı ve RR
        current_tier = current_season_data.get("CompetitiveTier")
        ranked_rating = current_season_data.get("RankedRating", 0)
        
        # Eğer güncel rank null ise Derecesiz göster
        if current_tier is None or current_tier == 0:
            current_tier = 0
            current_rank = "Derecesiz"
        else:
            current_rank = f"{get_rank_name(current_tier)} ({ranked_rating} RR)"
        
        # Peak rank için tüm sezonlardaki WinsByTier'ları kontrol et
        peak_tier = 0
        
        if seasonal_info and isinstance(seasonal_info, dict):
            for season_info in seasonal_info.values():
                if season_info and isinstance(season_info, dict):
                    # Önce CompetitiveTier'i kontrol et
                    season_tier = season_info.get("CompetitiveTier", 0)
                    if isinstance(season_tier, (int, float)) and season_tier > peak_tier:
                        peak_tier = int(season_tier)
                        
                    # WinsByTier'ları da kontrol et
                    wins_by_tier = season_info.get("WinsByTier")
                    if wins_by_tier and isinstance(wins_by_tier, dict):
                        # String olan tier'ları integer'a çevir ve en yükseğini bul
                        try:
                            tiers = []
                            for tier_key in wins_by_tier.keys():
                                if tier_key and str(tier_key).isdigit():
                                    tiers.append(int(tier_key))
                            
                            if tiers:
                                max_tier = max(tiers)
                                if max_tier > peak_tier:
                                    peak_tier = max_tier
                        except (ValueError, TypeError):
                            continue
        
        # Eğer peak rank bulunamadıysa güncel rank'i kullan
        if peak_tier == 0:
            peak_tier = current_tier
            
        result = (current_rank, get_rank_name(peak_tier), winrate)
        
        # Sonucu cache'e kaydet
        cache.set('ranks', puuid, result)
            
        return result
        
    except Exception as e:
        print(f"Rank bilgileri alınamadı: {e}")
        return "Derecesiz", "Derecesiz", "?" 