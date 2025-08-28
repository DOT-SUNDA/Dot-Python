<?php
session_start();

// ====== Konfigurasi ======
define('PORT', 5000);
define('IP_FILE', "ip_list.json");

// ====== Load IP ======
function load_ips() {
    if (file_exists(IP_FILE)) {
        return json_decode(file_get_contents(IP_FILE), true);
    }
    return [];
}

function save_ips($ip_list) {
    file_put_contents(IP_FILE, json_encode($ip_list, JSON_PRETTY_PRINT));
}

$ip_list = load_ips();

// ====== Proses Form ======
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_POST['action'])) {
        switch ($_POST['action']) {
            case 'add_ip':
                $ips = isset($_POST['ips']) ? explode("\n", str_replace("\r", "", $_POST['ips'])) : [];
                $ips = array_map('trim', $ips);
                $ips = array_filter($ips);
                
                $added = 0;
                foreach ($ips as $ip) {
                    if (!in_array($ip, $ip_list)) {
                        $ip_list[] = $ip;
                        $added++;
                    }
                }
                save_ips($ip_list);
                $_SESSION['results'] = ["✅ Berhasil menambahkan $added IP."];
                break;
                
            case 'delete_ip':
                $ip = $_POST['ip'] ?? '';
                if (($key = array_search($ip, $ip_list)) !== false) {
                    unset($ip_list[$key]);
                    $ip_list = array_values($ip_list);
                    save_ips($ip_list);
                    $_SESSION['results'] = ["🗑️ IP $ip dihapus."];
                }
                break;
                
            case 'clear_ip':
                $ip_list = [];
                save_ips($ip_list);
                $_SESSION['results'] = ["🧹 Semua IP dihapus."];
                break;
                
            case 'send_link':
                $links = isset($_POST['links']) ? explode("\n", str_replace("\r", "", $_POST['links'])) : [];
                $links = array_map('trim', $links);
                $links = array_filter($links);
                
                if (empty($ip_list)) {
                    $_SESSION['results'] = ["❌ Tidak ada IP yang ditambahkan."];
                    break;
                }
                
                $results = [];
                $ip_links_map = array_fill_keys($ip_list, []);
                
                foreach ($links as $i => $link) {
                    $target_ip = $ip_list[$i % count($ip_list)];
                    $ip_links_map[$target_ip][] = $link;
                }
                
                foreach ($ip_links_map as $ip => $links_for_ip) {
                    if (empty($links_for_ip)) continue;
                    
                    $combined_links = implode("\n", $links_for_ip);
                    $url = "http://$ip:" . PORT . "/update-link";
                    
                    $ch = curl_init();
                    curl_setopt($ch, CURLOPT_URL, $url);
                    curl_setopt($ch, CURLOPT_POST, true);
                    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode(["link" => $combined_links]));
                    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
                    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
                    
                    $response = curl_exec($ch);
                    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
                    
                    if (curl_error($ch)) {
                        $results[] = "$ip ← link → Error: " . curl_error($ch);
                    } else {
                        $response_data = json_decode($response, true);
                        $msg = isset($response_data['message']) ? $response_data['message'] : $response;
                        $results[] = "$ip ← " . count($links_for_ip) . " link → $msg";
                    }
                    
                    curl_close($ch);
                }
                
                $_SESSION['results'] = array_slice($results, 0, 20);
                break;
                
            case 'send_waktu':
                $waktu = [
                    "buka_jam" => intval($_POST['buka_jam'] ?? 0),
                    "buka_menit" => intval($_POST['buka_menit'] ?? 0),
                    "tutup_jam" => intval($_POST['tutup_jam'] ?? 0),
                    "tutup_menit" => intval($_POST['tutup_menit'] ?? 0),
                ];
                
                $results = [];
                foreach ($ip_list as $ip) {
                    $url = "http://$ip:" . PORT . "/update-waktu";
                    
                    $ch = curl_init();
                    curl_setopt($ch, CURLOPT_URL, $url);
                    curl_setopt($ch, CURLOPT_POST, true);
                    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($waktu));
                    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
                    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
                    
                    $response = curl_exec($ch);
                    
                    if (curl_error($ch)) {
                        $results[] = "$ip ← waktu → Error: " . curl_error($ch);
                    } else {
                        $response_data = json_decode($response, true);
                        $msg = isset($response_data['message']) ? $response_data['message'] : $response;
                        $results[] = "$ip ← waktu → $msg";
                    }
                    
                    curl_close($ch);
                }
                
                $_SESSION['results'] = array_slice($results, 0, 20);
                break;
                
            case 'start_script_target':
                $target = $_POST['target'] ?? '1';
                
                if (empty($ip_list)) {
                    header('Content-Type: application/json');
                    echo json_encode(["message" => "❌ Tidak ada IP untuk dijalankan."]);
                    exit;
                }
                
                $results = [];
                foreach ($ip_list as $ip) {
                    $url = "http://$ip:" . PORT . "/start-script";
                    
                    $ch = curl_init();
                    curl_setopt($ch, CURLOPT_URL, $url);
                    curl_setopt($ch, CURLOPT_POST, true);
                    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode(["target" => $target]));
                    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
                    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
                    
                    $response = curl_exec($ch);
                    
                    if (curl_error($ch)) {
                        $results[] = "$ip ← Start File $target → Error: " . curl_error($ch);
                    } else {
                        $response_data = json_decode($response, true);
                        $msg = isset($response_data['message']) ? $response_data['message'] : $response;
                        $results[] = "$ip ← Start File $target → $msg";
                    }
                    
                    curl_close($ch);
                }
                
                header('Content-Type: application/json');
                echo json_encode(["message" => "✅ Berhasil start file $target ke semua IP", "results" => $results]);
                exit;
                
            case 'stop_script':
                if (empty($ip_list)) {
                    header('Content-Type: application/json');
                    echo json_encode(["message" => "❌ Tidak ada IP untuk dihentikan."]);
                    exit;
                }
                
                $results = [];
                foreach ($ip_list as $ip) {
                    $url = "http://$ip:" . PORT . "/stop-script";
                    
                    $ch = curl_init();
                    curl_setopt($ch, CURLOPT_URL, $url);
                    curl_setopt($ch, CURLOPT_POST, true);
                    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([]));
                    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
                    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
                    
                    $response = curl_exec($ch);
                    
                    if (curl_error($ch)) {
                        $results[] = "$ip ← Stop → Error: " . curl_error($ch);
                    } else {
                        $response_data = json_decode($response, true);
                        $msg = isset($response_data['message']) ? $response_data['message'] : $response;
                        $results[] = "$ip ← Stop → $msg";
                    }
                    
                    curl_close($ch);
                }
                
                header('Content-Type: application/json');
                echo json_encode(["message" => "✅ Berhasil stop semua", "results" => $results]);
                exit;
        }
    }
    
    header("Location: " . $_SERVER['PHP_SELF']);
    exit;
}

// ====== Tampilkan HTML ======
$results = isset($_SESSION['results']) ? $_SESSION['results'] : [];
unset($_SESSION['results']);

// HTML Template
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Control Panel Multi RDP</title>
    <link href="http://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        .modal { display: none; }
    </style>
</head>
<body class="bg-gray-100 font-sans">
<div class="container mx-auto p-6 bg-white rounded-lg shadow-lg">
    <h2 class="text-2xl font-bold text-gray-800">Control Panel Multi RDP</h2>
    
    <div class="mt-6 grid grid-cols-3 sm:grid-cols-5 gap-4 text-center">
        <button id="addIpBtn" class="flex flex-col items-center bg-blue-100 hover:bg-blue-200 text-blue-600 p-3 rounded-lg">
            <!-- Icon Tambah -->
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            <span class="text-sm">Tambah IP</span>
        </button>
        
        <button id="sendLinkBtn" class="flex flex-col items-center bg-blue-100 hover:bg-blue-200 text-blue-600 p-3 rounded-lg">
            <!-- Icon Link -->
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 010 5.656m1.414-1.414a6 6 0 00-8.485-8.485m8.485 8.485L10.172 13.828" />
            </svg>
            <span class="text-sm">Kirim Link</span>
        </button>

        <button id="sendWaktuBtn" class="flex flex-col items-center bg-blue-100 hover:bg-blue-200 text-blue-600 p-3 rounded-lg">
            <!-- Icon Clock -->
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-sm">Kirim Waktu</span>
        </button>

        <button onclick="startFile(1)" class="flex flex-col items-center bg-purple-100 hover:bg-purple-200 text-purple-600 p-3 rounded-lg">
            <!-- Icon File 1 -->
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span class="text-sm">Start Awal</span>
        </button>

        <button onclick="startFile(2)" class="flex flex-col items-center bg-indigo-100 hover:bg-indigo-200 text-indigo-600 p-3 rounded-lg">
            <!-- Icon File 2 -->
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span class="text-sm">Start Loop</span>
        </button>

        <button id="stopBtn" class="flex flex-col items-center bg-red-100 hover:bg-red-200 text-red-600 p-3 rounded-lg">
            <!-- Icon Stop -->
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span class="text-sm">Stop</span>
        </button>
    </div>

    <?php if (!empty($ip_list)): ?>
    <div class="mt-6">
        <h4 class="text-lg font-semibold text-gray-700">Daftar IP Aktif:</h4>
        <ul class="list-disc pl-5">
            <?php foreach ($ip_list as $index => $ip): ?>
                <li class="flex justify-between items-center py-2">
                    <span class="text-gray-600"><?= $index + 1 ?>. <?= htmlspecialchars($ip) ?></span>
                    <form method="POST" action="" class="inline">
                        <input type="hidden" name="action" value="delete_ip">
                        <input type="hidden" name="ip" value="<?= htmlspecialchars($ip) ?>">
                        <button type="submit" class="bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600">Hapus</button>
                    </form>
                </li>
            <?php endforeach; ?>
        </ul>
        <form method="POST" action="" class="mt-4">
            <input type="hidden" name="action" value="clear_ip">
            <button type="submit" class="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600">Hapus Semua</button>
        </form>
    </div>
    <?php endif; ?>

    <?php if (!empty($results)): ?>
    <div class="mt-6 bg-blue-100 border-l-4 border-blue-500 text-blue-700 p-4 rounded">
        <h4 class="font-bold">Hasil:</h4>
        <?php foreach ($results as $res): ?>
            <p><?= htmlspecialchars($res) ?></p>
        <?php endforeach; ?>
    </div>
    <?php endif; ?>
</div>

<!-- Modal untuk Tambah IP -->
<div id="addIpModal" class="modal fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center">
    <div class="bg-white rounded-lg p-6 w-11/12 md:w-1/3">
        <span class="close cursor-pointer text-gray-500 float-right" id="closeAddIpModal">&times;</span>
        <h4 class="text-lg font-semibold">Tambah IP RDP</h4>
        <form method="POST" action="">
            <input type="hidden" name="action" value="add_ip">
            <label class="block mt-4">IP RDP (satu per baris):</label>
            <textarea name="ips" rows="5" class="border border-gray-300 rounded w-full p-2 mt-1" placeholder="192.168.1.10&#10;192.168.1.11"></textarea>
            <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded mt-4 hover:bg-blue-600">Tambah</button>
        </form>
    </div>
</div>

<!-- Modal untuk Kirim Link -->
<div id="sendLinkModal" class="modal fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center">
    <div class="bg-white rounded-lg p-6 w-11/12 md:w-1/3">
        <span class="close cursor-pointer text-gray-500 float-right" id="closeSendLinkModal">&times;</span>
        <h4 class="text-lg font-semibold">Kirim Link</h4>
        <form method="POST" action="">
            <input type="hidden" name="action" value="send_link">
            <label class="block mt-4">Link (satu per baris):</label>
            <textarea name="links" rows="5" class="border border-gray-300 rounded w-full p-2 mt-1" placeholder="http://example.com/page1&#10;http://example.com/page2"></textarea>
            <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded mt-4 hover:bg-blue-600">Kirim Link ke IP</button>
        </form>
    </div>
</div>

<!-- Modal untuk Kirim Waktu -->
<div id="sendWaktuModal" class="modal fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center">
    <div class="bg-white rounded-lg p-6 w-11/12 md:w-1/3">
        <span class="close cursor-pointer text-gray-500 float-right" id="closeSendWaktuModal">&times;</span>
        <h4 class="text-lg font-semibold">Kirim Waktu</h4>
        <form method="POST" action="">
            <input type="hidden" name="action" value="send_waktu">
            <label class="block mt-4">Jam Buka:</label>
            <input name="buka_jam" type="number" class="border border-gray-300 rounded w-full p-2 mt-1" placeholder="Jam Buka" min="0" max="23">
            <label class="block mt-4">Menit Buka:</label>
            <input name="buka_menit" type="number" class="border border-gray-300 rounded w-full p-2 mt-1" placeholder="Menit Buka" min="0" max="59">
            <label class="block mt-4">Jam Tutup:</label>
            <input name="tutup_jam" type="number" class="border border-gray-300 rounded w-full p-2 mt-1" placeholder="Jam Tutup" min="0" max="23">
            <label class="block mt-4">Menit Tutup:</label>
            <input name="tutup_menit" type="number" class="border border-gray-300 rounded w-full p-2 mt-1" placeholder="Menit Tutup" min="0" max="59">
            <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded mt-4 hover:bg-blue-600">Kirim Waktu ke Semua IP</button>
        </form>
    </div>
</div>

<script>
    // Menampilkan modal
    document.getElementById('addIpBtn').onclick = function() {
        document.getElementById('addIpModal').style.display = "flex";
    }
    document.getElementById('sendLinkBtn').onclick = function() {
        document.getElementById('sendLinkModal').style.display = "flex";
    }
    document.getElementById('sendWaktuBtn').onclick = function() {
        document.getElementById('sendWaktuModal').style.display = "flex";
    }

    // Menutup modal
    document.getElementById('closeAddIpModal').onclick = function() {
        document.getElementById('addIpModal').style.display = "none";
    }
    document.getElementById('closeSendLinkModal').onclick = function() {
        document.getElementById('sendLinkModal').style.display = "none";
    }
    document.getElementById('closeSendWaktuModal').onclick = function() {
        document.getElementById('sendWaktuModal').style.display = "none";
    }

    // Menutup modal jika klik di luar modal
    window.onclick = function(event) {
        if (event.target.className.includes('modal')) {
            event.target.style.display = "none";
        }
    }

    function startFile(target) {
        fetch('', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'action=start_script_target&target=' + target
        })
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            location.reload();
        })
        .catch(err => alert('Gagal start file ' + target + ': ' + err.message));
    }

    document.getElementById('stopBtn').onclick = () => {
        fetch('', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'action=stop_script'
        })
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            location.reload();
        })
        .catch(err => alert('Gagal stop: ' + err.message));
    };
</script>
</body>
</html>
