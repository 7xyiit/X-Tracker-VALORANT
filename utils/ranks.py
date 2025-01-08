from .colors import Colors
from .api import get_current_season_id
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
    try:
        response = requests.get(
            f'https://pd.{shard}.a.pvp.net/mmr/v1/players/{puuid}',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        rank_data = response.json()
        
        if not rank_data:
            return "Derecesiz", "Derecesiz"
            
        # Güncel sezon ID'sini al
        current_season = get_current_season_id(shard, headers)
        if not current_season:
            return "Derecesiz", "Derecesiz"
            
        # Güncel rank bilgisini bul
        queue_skills = rank_data.get("QueueSkills", {})
        competitive = queue_skills.get("competitive", {})
        seasonal_info = competitive.get("SeasonalInfoBySeasonID", {})
        
        # Güncel sezon rankı ve RR
        current_season_data = seasonal_info.get(current_season, {})
        current_tier = current_season_data.get("CompetitiveTier")
        ranked_rating = current_season_data.get("RankedRating", 0)
        
        # Eğer güncel rank null ise Derecesiz göster
        if current_tier is None:
            current_tier = 0
            current_rank = "Derecesiz"
        else:
            current_rank = f"{get_rank_name(current_tier)} ({ranked_rating} RR)"
        
        # Peak rank için tüm sezonlardaki WinsByTier'ları kontrol et
        peak_tier = 0
        for season_info in seasonal_info.values():
            if season_info:
                wins_by_tier = season_info.get("WinsByTier", {})
                if wins_by_tier:
                    # String olan tier'ları integer'a çevir ve en yükseğini bul
                    tiers = [int(tier) for tier in wins_by_tier.keys()]
                    if tiers:
                        max_tier = max(tiers)
                        if max_tier > peak_tier:
                            peak_tier = max_tier
        
        # Eğer peak rank bulunamadıysa güncel rank'i kullan
        if peak_tier == 0:
            peak_tier = current_tier
            
        return current_rank, get_rank_name(peak_tier)
    except Exception as e:
        return "Derecesiz", "Derecesiz" 