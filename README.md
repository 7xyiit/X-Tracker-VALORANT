<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proje Başlığı</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            height: 100vh;
            margin: 0;
            background-color: #f4f4f4;
        }
        header {
            text-align: center;
            margin-bottom: 30px;
        }
        header img {
            width: 150px;
            height: auto;
        }
        table {
            width: 80%;
            border-collapse: collapse;
            margin-top: 20px;
            text-align: center;
        }
        table th, table td {
            padding: 10px;
            border: 1px solid #ddd;
        }
        table th {
            background-color: #4CAF50;
            color: white;
        }
        table td img {
            width: 100px;
            height: 100px;
        }
    </style>
</head>
<body>

    <!-- Logo ve Başlık -->
    <header>
        <img src="assets/logo.png" alt="Logo">
    </header>

    <!-- Tablo -->
    <table>
        <tr>
            <th>Parti</th>
            <th>Ajan</th>
            <th>Oyuncu</th>
            <th>Skin</th>
            <th>Rank</th>
            <th>Peak Rank</th>
            <th>HS Oranı</th>
            <th>Seviye</th>
        </tr>
        <tr>
            <td><img src="assets/party_image1.jpg" alt="Parti 1"></td>
            <td><img src="assets/agent_image1.jpg" alt="Ajan 1"></td>
            <td><img src="assets/player_image1.jpg" alt="Oyuncu 1"></td>
            <td><img src="assets/skin_image1.jpg" alt="Skin 1"></td>
            <td><img src="assets/rank_image1.jpg" alt="Rank 1"></td>
            <td><img src="assets/peak_rank_image1.jpg" alt="Peak Rank 1"></td>
            <td><img src="assets/hs_rate_image1.jpg" alt="HS Oranı 1"></td>
            <td><img src="assets/level_image1.jpg" alt="Seviye 1"></td>
        </tr>
        <tr>
            <td><img src="assets/party_image2.jpg" alt="Parti 2"></td>
            <td><img src="assets/agent_image2.jpg" alt="Ajan 2"></td>
            <td><img src="assets/player_image2.jpg" alt="Oyuncu 2"></td>
            <td><img src="assets/skin_image2.jpg" alt="Skin 2"></td>
            <td><img src="assets/rank_image2.jpg" alt="Rank 2"></td>
            <td><img src="assets/peak_rank_image2.jpg" alt="Peak Rank 2"></td>
            <td><img src="assets/hs_rate_image2.jpg" alt="HS Oranı 2"></td>
            <td><img src="assets/level_image2.jpg" alt="Seviye 2"></td>
        </tr>
    </table>

</body>
</html>
