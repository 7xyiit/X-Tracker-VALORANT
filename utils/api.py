import requests
import base64
import os
from urllib3.exceptions import InsecureRequestWarning
from .colors import Colors
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_lockfile():
    try:
        lockfile_path = os.path.join(os.getenv('LOCALAPPDATA'), R'Riot Games\Riot Client\Config\lockfile')
        
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
            "Iso": "\033[38;5;202m",        # Turuncu-Kırmızı
            # Initiators
            "Sova": "\033[38;5;75m",        # Açık Mavi
            "Breach": "\033[38;5;166m",     # Turuncu-Kahve
            "Skye": "\033[38;5;114m",       # Yeşil
            "KAY/O": "\033[38;5;87m",       # Turkuaz
            "Fade": "\033[38;5;54m",        # Koyu Mor
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
            "Deadlock": "\033[38;5;145m"    # Gri
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
            
        return party_members
    except Exception as e:
        print(f"Parti bilgileri alınamadı: {e}")
        return {}

def get_match_loadouts(match_id, region, shard, headers):
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
    try:
        response = requests.get(
            f'https://glz-{region}-1.{shard}.a.pvp.net/core-game/v1/matches/{match_id}',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        match_data = response.json()
        
        # Oyuncu seviyelerini al
        player_levels = {}
        for player in match_data.get("Players", []):
            player_id = player.get("Subject")
            player_identity = player.get("PlayerIdentity", {})
            account_level = player_identity.get("AccountLevel", 0)
            player_levels[player_id] = account_level
            
        match_data["PlayerLevels"] = player_levels
        return match_data
    except Exception as e:
        print(f"Maç detayları alma hatası: {e}")
        return None

def get_player_names(puuids, shard, headers):
    try:
        response = requests.put(
            f'https://pd.{shard}.a.pvp.net/name-service/v2/players',
            headers=headers,
            json=puuids,
            verify=False
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Oyuncu isimleri alma hatası: {e}")
        return None

def get_current_season_id(shard, headers):
    try:
        response = requests.get(
            f'https://shared.{shard}.a.pvp.net/content-service/v3/content',
            headers=headers,
            verify=False
        )
        response.raise_for_status()
        content_data = response.json()
        
        # Aktif sezonu bul (isActive=true ve type=act)
        for season in content_data.get("Seasons", []):
            if season.get("IsActive") and season.get("Type") == "act":
                return season.get("ID")
        return None
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