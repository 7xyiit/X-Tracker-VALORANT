import time

# Cache süresi (15 dakika - bir oyun süresi)
# Rank bilgileri çok sık değişmez, rate limiting'i önlemek için uzun tutuyoruz
CACHE_DURATION = 900  # saniye (15 dakika)

class Cache:
    def __init__(self):
        self.data = {
            'ranks': {},      # puuid -> (rank_data, timestamp)
            'hs_stats': {},   # puuid -> (hs_data, timestamp)
            'party_info': {}, # puuid -> (party_data, timestamp)
            'match_details': {}, # match_id -> (match_data, timestamp)
            'match_loadouts': {}, # match_id -> (loadouts_data, timestamp)
            'player_names': {}, # puuid_list_str -> (names_data, timestamp)
            'season_info': {}, # shard -> (season_data, timestamp)
            'player_level': {} # puuid -> (level_data, timestamp)
        }
    
    def get(self, cache_type, key):
        """Cache'den veri al"""
        if cache_type in self.data and key in self.data[cache_type]:
            data, timestamp = self.data[cache_type][key]
            if time.time() - timestamp < CACHE_DURATION:
                return data
        return None
    
    def set(self, cache_type, key, value):
        """Cache'e veri kaydet"""
        if cache_type in self.data:
            self.data[cache_type][key] = (value, time.time())
    
    def clear(self, cache_type=None):
        """Cache'i temizle"""
        if cache_type:
            if cache_type in self.data:
                self.data[cache_type].clear()
        else:
            for cache_dict in self.data.values():
                cache_dict.clear()

# Global cache instance
cache = Cache() 