import requests
import base64
import os
from .colors import Colors
from .cache import cache

# urllib3 uyarılarını devre dışı bırak
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except (ImportError, AttributeError):
    pass

def get_lockfile():
    try:
        localappdata = os.getenv('LOCALAPPDATA')
        if not localappdata:
            print(f"{Colors.ERROR}LOCALAPPDATA environment variable bulunamadı!{Colors.RESET}")
            return None
            
        lockfile_path = os.path.join(localappdata, R'Riot Games\Riot Client\Config\lockfile')
        
        if not os.path.isfile(lockfile_path):
            print(f"{Colors.ERROR}Valorant çalışmıyor! Lütfen oyunu başlatın.{Colors.RESET}")
            return None
            
        with open(lockfile_path, 'r') as file:
            data = file.read().split(':')
            keys = ['name', 'pid', 'port', 'password', 'protocol']
            return dict(zip(keys, data))
    except Exception as e:
        print(f"{Colors.ERROR}Lockfile okuma hatası: {e}{Colors.RESET}")
        return None

def get_local_headers(lockfile):
    if not lockfile:
        return None
        
    auth = base64.b64encode(f'riot:{lockfile["password"]}'.encode()).decode()
    return {
        'Authorization': f'Basic {auth}'
    }

def get_player_level(puuid, shard, headers):
    """Oyuncu seviyesini al"""
    # Önce cache'e bak
    cached_data = cache.get('player_level', puuid)
    if cached_data:
        return cached_data
        
    try:
        # İlk olarak account-xp endpoint'i deneyelim (sadece kendi seviyesi için çalışır)
        response = requests.get(
            f'https://pd.{shard}.a.pvp.net/account-xp/v1/players/{puuid}',
            headers=headers,
            verify=False
        )
        
        if response.status_code == 200:
            level_data = response.json()
            
            # Farklı veri yapılarını deneyerek seviye bilgisini bul
            level = None
            if 'Progress' in level_data:
                level = level_data['Progress'].get('Level', 0)
            elif 'Level' in level_data:
                level = level_data['Level']
            elif 'AccountLevel' in level_data:
                level = level_data['AccountLevel']
            
            if level is not None and level > 0:
                # Sonucu cache'e kaydet
                cache.set('player_level', puuid, level)
                return level
        
        # Eğer account-xp endpoint'i çalışmazsa, alternatif yol deneyelim
        # Player MMR endpoint'i kullanarak seviye bilgisini almaya çalış
        mmr_response = requests.get(
            f'https://pd.{shard}.a.pvp.net/mmr/v1/players/{puuid}',
            headers=headers,
            verify=False
        )
        
        if mmr_response.status_code == 200:
            mmr_data = mmr_response.json()
            
            # MMR verilerinden seviye bilgisini almaya çalış
            level = mmr_data.get('AccountLevel', 0)
            
            if level > 0:
                # Sonucu cache'e kaydet
                cache.set('player_level', puuid, level)
                return level
        
        return "Gizli"  # Seviye gizlenmiş
        
    except Exception as e:
        print(f"Oyuncu seviyesi alınamadı ({puuid[:8]}...): {e}")
        return "Gizli"

def get_vandal_skins():
    VANDAL_UUID = "9c82e19d-4575-0200-1a81-3eacf00cf872"
    try:
        response = requests.get(f"https://valorant-api.com/v1/weapons/{VANDAL_UUID}?language=tr-TR")
        response.raise_for_status()
        skins_data = response.json()["data"]["skins"]
        
        # UUID'leri skin isimleriyle eşleştir
        skin_dict = {}
        
        # Her skinin ana displayName'ini al
        for skin in skins_data:
            skin_uuid = skin["uuid"]
            display_name = skin["displayName"]
            
            # İsmi düzenle
            if display_name == "VANDAL":
                display_name = "Standart Vandal"
            else:
                # Büyük harfli isimleri düzelt
                words = display_name.split()
                display_name = " ".join(word.capitalize() for word in words)
            
            skin_dict[skin_uuid] = display_name
        
        return skin_dict
    except Exception as e:
        print(f"Vandal skinleri alınamadı: {e}")
        return {}

def get_agent_names():
    try:
        response = requests.get("https://valorant-api.com/v1/agents?isPlayableCharacter=True")
        response.raise_for_status()
        agents_data = response.json()["data"]
        
        # Her ajan için özel renkler
        agent_colors = {
            # Duelists
            "Jett": "\033[38;5;153m",      # Açık Mavi
            "Phoenix": "\033[38;5;208m",    # Turuncu
            "Raze": "\033[38;5;214m",       # Koyu Sarı
            "Reyna": "\033[38;5;165m",      # Mor
            "Yoru": "\033[38;5;27m",        # Mavi
            "Neon": "\033[38;5;51m",        # Neon Mavi
            "Iso": "\033[38;5;147m",        # Açık Morumsu
            # Initiators
            "Sova": "\033[38;5;75m",        # Açık Mavi
            "Breach": "\033[38;5;166m",     # Turuncu-Kahve
            "Skye": "\033[38;5;114m",       # Yeşil
            "KAY/O": "\033[38;5;87m",       # Turkuaz
            "Fade": "\033[38;5;61m",        # Açık Lacivert
            "Gekko": "\033[38;5;84m",       # Açık Yeşil
            # Controllers
            "Brimstone": "\033[38;5;130m",  # Kahverengi
            "Viper": "\033[38;5;40m",       # Yeşil
            "Omen": "\033[38;5;91m",        # Mor
            "Astra": "\033[38;5;171m",      # Pembe
            "Harbor": "\033[38;5;31m",      # Deniz Mavisi
            # Sentinels
            "Killjoy": "\033[38;5;226m",    # Sarı
            "Cypher": "\033[38;5;251m",     # Gümüş
            "Sage": "\033[38;5;123m",       # Açık Turkuaz
            "Chamber": "\033[38;5;220m",    # Altın
            "Deadlock": "\033[38;5;117m",   # Buz Mavisi
            # Yeni Ajanlar
            "Vyse": "\033[38;5;140m",       # Açık-Koyu Mor Arası
            "Clove": "\033[38;5;218m",      # Tatlı Açık Pembe
            "Tejo": "\033[38;5;215m"        # Hafif Açık Turuncu
        }
        
        # UUID'leri ajan isimleriyle eşleştir
        agent_dict = {}
        for agent in agents_data:
            agent_name = agent["displayName"]
            color = agent_colors.get(agent_name, Colors.RESET)
            # UUID'yi küçük harfe çevir
            agent_dict[agent["uuid"].lower()] = f"{color}{agent_name}{Colors.RESET}"
        
        return agent_dict
    except Exception as e:
        print(f"Ajan isimleri alınamadı: {e}")
        return {}

def get_player_party_info(puuid, region, shard, headers):
    # Önce cache'e bak
    cached_data = cache.get('party_info', puuid)
    if cached_data:
        return cached_data
        
    try:
        # Oyuncunun parti bilgisini al
        response = requests.get(
            f'https://glz-{region}-1.{shard}.a.pvp.net/parties/v1/players/{puuid}',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        party_data = response.json()
        party_id = party_data.get("CurrentPartyID")
        
        if not party_id:
            return {}
            
        # Parti üyelerini al
        response = requests.get(
            f'https://glz-{region}-1.{shard}.a.pvp.net/parties/v1/parties/{party_id}',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        party_details = response.json()
        
        # Parti üyelerinin PUUID'lerini topla
        party_members = set()
        for member in party_details.get("Members", []):
            party_members.add(member.get("Subject"))
            
        # Sonucu cache'e kaydet
        cache.set('party_info', puuid, party_members)
            
        return party_members
    except Exception as e:
        print(f"Parti bilgileri alınamadı: {e}")
        return {}

def get_match_loadouts(match_id, region, shard, headers):
    # Önce cache'e bak
    cached_data = cache.get('match_loadouts', match_id)
    if cached_data:
        return cached_data
        
    VANDAL_UUID = "9c82e19d-4575-0200-1a81-3eacf00cf872"
    try:
        response = requests.get(
            f'https://glz-{region}-1.{shard}.a.pvp.net/core-game/v1/matches/{match_id}/loadouts',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        loadouts_data = response.json()
        
        # Oyuncu skinlerini ve ajanlarını saklamak için sözlükler
        player_skins = {}
        player_agents = {}
        
        for loadout in loadouts_data.get("Loadouts", []):
            player_id = loadout.get("Loadout", {}).get("Subject")
            items = loadout.get("Loadout", {}).get("Items", {})
            
            # Ajan bilgisini kaydet (küçük harfe çevirerek)
            agent_id = loadout.get("CharacterID", "").lower()
            if agent_id:
                player_agents[player_id] = agent_id
            
            # Vandal'ı bul
            if VANDAL_UUID in items:
                vandal_data = items[VANDAL_UUID]
                sockets = vandal_data.get("Sockets", {})
                
                # İkinci socket'i bul (bcef87d6-209b-46c6-8b19-fbe40bd95abc)
                socket_id = "bcef87d6-209b-46c6-8b19-fbe40bd95abc"
                if socket_id in sockets:
                    socket_data = sockets[socket_id]
                    if "Item" in socket_data and "ID" in socket_data["Item"]:
                        skin_id = socket_data["Item"]["ID"]
                        player_skins[player_id] = skin_id
        
        loadouts_data["PlayerSkins"] = player_skins
        loadouts_data["PlayerAgents"] = player_agents
        
        # Sonucu cache'e kaydet
        cache.set('match_loadouts', match_id, loadouts_data)
        
        return loadouts_data
    except Exception as e:
        print(f"Loadout bilgileri alınamadı: {e}")
        return None

def get_player_puuid(port, headers):
    try:
        response = requests.get(
            f'https://127.0.0.1:{port}/entitlements/v1/token',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        return response.json().get('subject')
    except Exception as e:
        print(f"PUUID alma hatası: {e}")
        return None

def get_match_id(puuid, region, shard, headers):
    try:
        response = requests.get(
            f'https://glz-{region}-1.{shard}.a.pvp.net/core-game/v1/players/{puuid}',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        data = response.json()
        return data.get("MatchID")
    except Exception as e:
        print(f"Match ID alma hatası: {e}")
        return None

def get_match_details(match_id, region, shard, headers):
    # Önce cache'e bak
    cached_data = cache.get('match_details', match_id)
    if cached_data:
        return cached_data
        
    try:
        response = requests.get(
            f'https://glz-{region}-1.{shard}.a.pvp.net/core-game/v1/matches/{match_id}',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        match_data = response.json()
        
        # Core-game endpoint'inden gelen PlayerIdentity bilgilerini kontrol et
        player_levels = {}
        
        for player in match_data.get("Players", []):
            player_id = player.get("Subject")
            player_identity = player.get("PlayerIdentity", {})
            account_level = player_identity.get("AccountLevel", 0)
            hide_account_level = player_identity.get("HideAccountLevel", False)
            
            if hide_account_level or account_level == 0:
                player_levels[player_id] = "Gizli"
            elif account_level > 0:
                player_levels[player_id] = account_level
        
        # Eğer core-game'den seviye bilgisi alındıysa match_data'ya ekle
        if player_levels:
            match_data["PlayerLevels"] = player_levels
        
        # Sonucu cache'e kaydet
        cache.set('match_details', match_id, match_data)
        
        return match_data
    except Exception as e:
        print(f"Maç detayları alma hatası: {e}")
        return None

def get_player_names(puuids, shard, headers):
    # Puuid listesini string'e çevir (cache key olarak kullanmak için)
    puuid_key = ','.join(sorted(puuids))
    
    # Önce cache'e bak
    cached_data = cache.get('player_names', puuid_key)
    if cached_data:
        return cached_data
        
    try:
        response = requests.put(
            f'https://pd.{shard}.a.pvp.net/name-service/v2/players',
            headers=headers,
            json=puuids,
            verify=False
        )
        response.raise_for_status()
        names_data = response.json()
        
        # Sonucu cache'e kaydet
        cache.set('player_names', puuid_key, names_data)
        
        return names_data
    except Exception as e:
        print(f"Oyuncu isimleri alma hatası: {e}")
        return None

def get_current_season_id(shard, headers):
    # Önce cache'e bak
    cached_data = cache.get('season_info', shard)
    if cached_data:
        return cached_data
        
    try:
        response = requests.get(
            f'https://shared.{shard}.a.pvp.net/content-service/v3/content',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        content_data = response.json()
        
        # Aktif sezonu bul (isActive=true ve type=act)
        season_id = None
        for season in content_data.get("Seasons", []):
            if season.get("IsActive") and season.get("Type") == "act":
                season_id = season.get("ID")
                break
                
        # Sonucu cache'e kaydet
        if season_id:
            cache.set('season_info', shard, season_id)
            
        return season_id
    except Exception as e:
        print(f"Sezon bilgisi alınamadı: {e}")
        return None

def get_version_and_platform():
    client_platform = "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjIyNjMxLjIyODgiLA0KCSJwbGF0Zm9ybUNoaXBzZXQiOiAiVW5rbm93biINCn0="
    
    try:
        version_response = requests.get("https://valorant-api.com/v1/version")
        version_data = version_response.json()
        client_version = version_data["data"]["riotClientVersion"]
        return client_platform, client_version
    except Exception as e:
        print(f"Versiyon bilgisi alınamadı: {e}")
        return None, None

def get_region_and_shard():
    # Şimdilik sabit değerler, daha sonra otomatik tespit edilebilir
    return "eu", "eu"

def get_coregame_token(port, headers):
    try:
        response = requests.get(
            f'https://127.0.0.1:{port}/entitlements/v1/token',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        data = response.json()
        return data.get("accessToken"), data.get("token")
    except Exception as e:
        print(f"Token alma hatası: {e}")
        return None, None