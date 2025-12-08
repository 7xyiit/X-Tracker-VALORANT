"""
X-Tracker Web API Servisi
Oyun bilgilerini ve oyuncu Vandal skinlerini web sitesinde gösterir
"""
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import os
import sys

# Parent dizini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.valorant_api import ValorantAPIService

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# ValorantAPI servisi
valorant_api = ValorantAPIService()

# Cache için global değişkenler
_vandal_skins_cache = None
_current_game_data = None


def get_vandal_skins_with_icons():
    """Vandal skinlerini displayIcon ile birlikte cache'le"""
    global _vandal_skins_cache
    if _vandal_skins_cache is None:
        from config.settings import VANDAL_UUID
        _vandal_skins_cache = valorant_api.get_weapon_skins_by_weapon(VANDAL_UUID)
    return _vandal_skins_cache


def set_game_data(game_info: dict):
    """Oyun verisini web için kaydet"""
    global _current_game_data
    _current_game_data = game_info


def get_game_data():
    """Mevcut oyun verisini döndür"""
    return _current_game_data


@app.route('/')
def index():
    """Ana sayfa - Oyuncu tablosu"""
    return render_template('index.html')


@app.route('/api/game')
def get_current_game():
    """
    Mevcut oyun bilgilerini döndürür (oyuncular ve Vandal skinleri dahil)
    
    Returns:
        JSON: {
            "status": "success" | "no_game",
            "match_id": str,
            "players": [
                {
                    "game_name": str,
                    "tag_line": str,
                    "team_id": str,
                    "agent_name": str,
                    "rank": str,
                    "level": int,
                    "vandal_skin": str,
                    "skin_uuid": str,
                    "skin_icon": str (URL)
                }
            ]
        }
    """
    game_data = get_game_data()
    
    if not game_data:
        return jsonify({
            "status": "no_game",
            "message": "Aktif oyun yok"
        })
    
    # Vandal skin ikonlarını al
    vandal_skins = get_vandal_skins_with_icons()
    
    # Oyuncu verilerine skin icon ekle
    players_with_icons = []
    for player in game_data.get("players", []):
        skin_uuid = player.get("skin_uuid", "").lower()
        skin_data = vandal_skins.get(skin_uuid, {})
        
        players_with_icons.append({
            **player,
            "skin_icon": skin_data.get("displayIcon", "")
        })
    
    return jsonify({
        "status": "success",
        "match_id": game_data.get("match_id"),
        "players": players_with_icons
    })


@app.route('/api/game/update', methods=['POST'])
def update_game_data():
    """
    Oyun verisini güncelle (tracker'dan çağrılır)
    """
    data = request.get_json()
    if data:
        set_game_data(data)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Veri yok"}), 400


@app.route('/api/skin/<skin_uuid>')
def get_skin_icon(skin_uuid):
    """
    Belirli bir Vandal skin'inin bilgilerini ve ikonunu döndürür
    """
    vandal_skins = get_vandal_skins_with_icons()
    skin_uuid_lower = skin_uuid.lower()
    
    if skin_uuid_lower in vandal_skins:
        return jsonify({
            "status": "success",
            "data": {
                "uuid": skin_uuid_lower,
                **vandal_skins[skin_uuid_lower]
            }
        })
    
    return jsonify({
        "status": "error",
        "message": "Skin bulunamadı"
    }), 404


@app.route('/api/vandal-skins')
def get_all_vandal_skins():
    """
    Tüm Vandal skinlerini döndürür
    """
    skins = get_vandal_skins_with_icons()
    
    result = []
    for uuid, data in skins.items():
        result.append({
            "uuid": uuid,
            **data
        })
    
    return jsonify({
        "status": "success",
        "count": len(result),
        "data": result
    })


@app.route('/api/refresh')
def refresh_cache():
    """Cache'i yeniler"""
    global _vandal_skins_cache
    _vandal_skins_cache = None
    get_vandal_skins_with_icons()
    
    return jsonify({
        "status": "success",
        "message": "Cache yenilendi"
    })


if __name__ == '__main__':
    print("🌐 X-Tracker Web başlatılıyor...")
    print("📍 http://localhost:5000 adresinde çalışıyor")
    print("")
    print("📍 API Endpoints:")
    print("   GET  /api/game         - Mevcut oyun bilgileri")
    print("   POST /api/game/update  - Oyun verisini güncelle")
    print("   GET  /api/skin/<uuid>  - Skin bilgisi")
    print("   GET  /api/vandal-skins - Tüm Vandal skinleri")
    print("   GET  /api/refresh      - Cache yenile")
    print("")
    app.run(debug=True, host='0.0.0.0', port=5000)
