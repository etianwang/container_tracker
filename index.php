<?php
declare(strict_types=1);

const DB_FILE = __DIR__ . '/data/tracker.sqlite';
const CACHE_TTL = 43200;
const MAX_HISTORY = 60;

$carriers = [
    'maersk' => ['Maersk Line'],
    'msc' => ['MSC'],
    'cosco' => ['COSCO Shipping'],
    'oocl' => ['OOCL'],
    'hapag' => ['Hapag-Lloyd'],
    'one' => ['ONE'],
    'zim' => ['ZIM'],
];

$prefixes = [
    'MSKU'=>['Maersk Line','maersk'], 'MRKU'=>['Maersk Line','maersk'], 'MRSU'=>['Maersk Line','maersk'],
    'SUDU'=>['Hamburg Sud (Maersk)','maersk'], 'SEAU'=>['Sealand (Maersk)','maersk'], 'TEMU'=>['Textainer / Maersk','maersk'],
    'MSCU'=>['MSC','msc'], 'MEDU'=>['MSC','msc'], 'CMDU'=>['CMA CGM','cmacgm'], 'APZU'=>['APL (CMA CGM)','cmacgm'],
    'COSU'=>['COSCO Shipping','cosco'], 'CCLU'=>['COSCO (CCL)','cosco'], 'CSNU'=>['COSCO / Sealand','cosco'],
    'HDMU'=>['HMM','hmm'], 'EGLV'=>['Evergreen','evergreen'], 'UETU'=>['Evergreen','evergreen'],
    'YMLU'=>['Yang Ming','yangming'], 'OOLU'=>['OOCL','oocl'], 'OOCU'=>['OOCL','oocl'],
    'HLCU'=>['Hapag-Lloyd','hapag'], 'HLXU'=>['Hapag-Lloyd','hapag'], 'ONEU'=>['ONE','one'], 'ZIMU'=>['ZIM','zim'], 'PCIU'=>['PIL','pil'], 'WHLU'=>['Wan Hai Lines','wanhai'],
    'TGHU'=>['Triton International','maersk'], 'TGBU'=>['Triton International','maersk'], 'TCKU'=>['Triton International','maersk'],
    'TIIU'=>['Triton International','maersk'], 'TRHU'=>['Triton International','maersk'], 'CAAU'=>['Triton International','maersk'],
    'DFSU'=>['Triton International','maersk'], 'BANQ'=>['Beacon Intermodal','maersk'], 'FFAU'=>['Florens Container','maersk'],
    'CXDU'=>['China Shipping','cosco'], 'SEKU'=>['Seaco','maersk'],
];

function json_response(array $data, int $status = 200): never {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function db(): PDO {
    static $db;
    if ($db) return $db;
    if (!is_dir(__DIR__ . '/data')) mkdir(__DIR__ . '/data', 0775, true);
    $db = new PDO('sqlite:' . DB_FILE, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    $db->exec('PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, container TEXT, carrier TEXT, time TEXT, note TEXT); CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, container TEXT, carrier TEXT, carrier_name TEXT, candidates TEXT, status TEXT, payload TEXT, error TEXT, recorded INTEGER DEFAULT 0, created_at INTEGER); CREATE TABLE IF NOT EXISTS cache (cache_key TEXT PRIMARY KEY, payload TEXT, expires_at INTEGER)');
    $columns = $db->query('PRAGMA table_info(jobs)')->fetchAll(PDO::FETCH_COLUMN, 1);
    if (!in_array('carrier_name', $columns, true)) $db->exec('ALTER TABLE jobs ADD COLUMN carrier_name TEXT');
    if (!in_array('candidates', $columns, true)) $db->exec('ALTER TABLE jobs ADD COLUMN candidates TEXT');
    return $db;
}

function history(): array {
    return db()->query('SELECT id, container, carrier, time, note FROM history ORDER BY time DESC LIMIT ' . MAX_HISTORY)->fetchAll(PDO::FETCH_ASSOC);
}

function python_bin(): string {
    if (PHP_OS_FAMILY === 'Windows') return 'py -3.12';
    return escapeshellcmd(getenv('TRACKER_PYTHON') ?: 'python3.12');
}

function queue_job(string $container, string $carrier, string $carrier_name, array $candidates): string {
    $db = db(); $db->exec('BEGIN IMMEDIATE');
    $active = $db->prepare("SELECT id FROM jobs WHERE container=? AND carrier=? AND status IN ('queued', 'running') ORDER BY created_at DESC LIMIT 1");
    $active->execute([$container, $carrier]);
    if ($id = $active->fetchColumn()) { $db->commit(); return $id; }
    $id = bin2hex(random_bytes(12));
    $db->prepare('INSERT INTO jobs (id, container, carrier, carrier_name, candidates, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)')->execute([$id, $container, $carrier, $carrier_name, json_encode($candidates), 'queued', time()]);
    $db->commit();
    if (PHP_OS_FAMILY === 'Windows') {
        $command = 'start "" /b ' . python_bin() . ' ' . escapeshellarg(__DIR__ . '/tracker_worker.py') . ' ' . escapeshellarg(DB_FILE) . ' ' . escapeshellarg($id) . ' >NUL 2>NUL';
        pclose(popen('cmd /c ' . $command, 'r'));
    } else {
        $command = python_bin() . ' ' . escapeshellarg(__DIR__ . '/tracker_worker.py') . ' ' . escapeshellarg(DB_FILE) . ' ' . escapeshellarg($id) . ' >/dev/null 2>&1 &';
        exec($command);
    }
    return $id;
}

function add_history(string $container, string $carrier): array {
    $db = db(); $db->exec('BEGIN IMMEDIATE');
    $db->prepare('DELETE FROM history WHERE container=?')->execute([$container]);
    $db->prepare('INSERT INTO history (id, container, carrier, time, note) VALUES (?, ?, ?, ?, ?)')->execute([bin2hex(random_bytes(8)), $container, $carrier, date(DATE_ATOM), '']);
    $db->exec('DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY time DESC LIMIT ' . MAX_HISTORY . ')');
    $db->commit(); return history();
}

function container_no(string $value): string {
    $value = strtoupper((string) preg_replace('/\s+/', '', $value));
    if (!preg_match('/^[A-Z]{4}\d{7}$/', $value)) throw new InvalidArgumentException('箱号格式应为 4 个字母加 7 个数字，例如 MRSU6845613。');
    return $value;
}

function request_data(): array {
    $json = json_decode((string) file_get_contents('php://input'), true);
    return is_array($json) ? $json : $_POST;
}

function tracker_result(string $container, string $carrier): array {
    $manual_urls = [
        'oocl' => 'https://www.oocl.com/eng/ourservices/eservices/cargotracking/Pages/cargotracking.aspx?searchType=cont&SEARCH_NUMBER=',
        'hapag' => 'https://www.hapag-lloyd.com/en/online-business/track/track-by-container-solution.html?container=',
        'one' => 'https://ecomm.one-line.com/one-ecom/manage-shipment/cargo-tracking?searchType=CONTAINER&searchValue=',
        'zim' => 'https://www.zim.com/tools/track-a-shipment?containerNumber=',
    ];
    if (!in_array($carrier, ['maersk', 'msc', 'cosco', ...array_keys($manual_urls)], true)) {
        throw new InvalidArgumentException('该承运商尚未接入站内实时查询。');
    }
    if (isset($manual_urls[$carrier])) {
        return ['manual_url' => $manual_urls[$carrier] . rawurlencode($container)];
    }
    $cache_key = $carrier . '-v4-' . $container;
    $row = db()->prepare('SELECT payload FROM cache WHERE cache_key=? AND expires_at>?'); $row->execute([$cache_key, time()]);
    if ($cached = $row->fetchColumn()) {
        $cached = json_decode($cached, true);
        if (is_array($cached)) return $cached + ['cached' => true];
    }
    $command = python_bin() . ' ' . escapeshellarg(__DIR__ . '/tracker_cli.py') . ' '
        . escapeshellarg($container) . ' ' . escapeshellarg($carrier);
    $output = shell_exec($command) ?? '';
    if (!preg_match('/^TRACKER_JSON=(.+)$/m', $output, $match)) {
        throw new RuntimeException('实时查询进程未返回结果。');
    }
    $payload = json_decode($match[1], true);
    if (!is_array($payload) || !($payload['ok'] ?? false)) {
        throw new RuntimeException('实时查询失败，请稍后重试。');
    }
    $result = $payload['result'];
    db()->prepare('INSERT OR REPLACE INTO cache (cache_key, payload, expires_at) VALUES (?, ?, ?)')->execute([$cache_key, json_encode($result, JSON_UNESCAPED_UNICODE), time() + CACHE_TTL]);
    return $result + ['cached' => false];
}

function cached_tracker_result(string $container, string $carrier): ?array {
    $row = db()->prepare('SELECT payload FROM cache WHERE cache_key=? AND expires_at>?'); $row->execute([$carrier . '-v4-' . $container, time()]);
    $result = json_decode((string) $row->fetchColumn(), true);
    return is_array($result) ? $result + ['cached' => true] : null;
}

if (isset($_GET['action'])) {
    try {
        $action = $_GET['action'];
        if ($action === 'history') json_response(['items' => history()]);
        $data = request_data();
        if ($action === 'track') {
            $no = container_no((string) ($data['container'] ?? ''));
            $selected = (string) ($data['carrier'] ?? 'auto');
            global $prefixes, $carriers;
            if ($selected === 'auto') {
                [$name, $key] = $prefixes[substr($no, 0, 4)] ?? ['自动轮询承运商', ''];
                if (in_array($key, ['oocl', 'hapag', 'one', 'zim'], true)) {
                    $candidates = [$key];
                } else {
                    $live = ['maersk', 'msc', 'cosco'];
                    $candidates = array_values(array_unique(array_filter([$key, ...$live], fn($item) => in_array($item, $live, true))));
                    $key = $candidates[0];
                }
            } else {
                if (!isset($carriers[$selected])) throw new InvalidArgumentException('无效的承运商。');
                [$name] = $carriers[$selected]; $key = $selected;
                $candidates = [$key];
            }
            if (in_array($key, ['oocl', 'hapag', 'one', 'zim'], true)) {
                $result = tracker_result($no, $key); $result['container'] = $no; $result['carrier'] = $name;
                json_response(['result' => $result, 'items' => add_history($no, $name)]);
            }
            if ($cached = cached_tracker_result($no, $key)) {
                $cached['container'] = $no; $cached['carrier'] = $name;
                $id = bin2hex(random_bytes(12));
                db()->prepare('INSERT INTO jobs (id, container, carrier, carrier_name, status, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)')->execute([$id, $no, $key, $name, 'done', json_encode($cached, JSON_UNESCAPED_UNICODE), time()]);
                json_response(['job' => ['id' => $id, 'container' => $no, 'carrier' => $name]]);
            }
            json_response(['job' => ['id' => queue_job($no, $key, $name, $candidates), 'container' => $no, 'carrier' => $name]]);
        }
        if ($action === 'job') {
            $id = (string) ($_GET['id'] ?? '');
            $job = db()->prepare('SELECT * FROM jobs WHERE id=?'); $job->execute([$id]); $job = $job->fetch(PDO::FETCH_ASSOC);
            if (!$job) json_response(['error' => '查询任务不存在。'], 404);
            if ($job['status'] === 'done' && !$job['recorded']) {
                db()->prepare('UPDATE jobs SET recorded=1 WHERE id=? AND recorded=0')->execute([$id]);
                add_history($job['container'], $job['carrier_name']);
                db()->prepare('INSERT OR REPLACE INTO cache (cache_key, payload, expires_at) VALUES (?, ?, ?)')->execute([$job['carrier'] . '-v4-' . $job['container'], $job['payload'], time() + CACHE_TTL]);
            }
            json_response(['job' => ['status' => $job['status'], 'result' => $job['payload'] ? json_decode($job['payload'], true) : null, 'error' => $job['error']]]);
        }
        if ($action === 'note') {
            $id = (string) ($data['id'] ?? ''); $note = trim((string) ($data['note'] ?? ''));
            db()->prepare('UPDATE history SET note=? WHERE id=?')->execute([mb_substr($note, 0, 300), $id]);
            json_response(['items' => history()]);
        }
        if ($action === 'delete') {
            $id = (string) ($data['id'] ?? ''); db()->prepare('DELETE FROM history WHERE id=?')->execute([$id]); json_response(['items' => history()]);
        }
        if ($action === 'clear') { db()->exec('DELETE FROM history'); json_response(['items' => []]); }
        json_response(['error' => '未知操作。'], 404);
    } catch (InvalidArgumentException $e) {
        json_response(['error' => $e->getMessage()], 422);
    } catch (RuntimeException $e) {
        json_response(['error' => $e->getMessage()], 502);
    } catch (Throwable) {
        json_response(['error' => '服务器处理失败。'], 500);
    }
}
?>
<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Honsen Africa · Container Tracker</title>
<style>
:root{--bg:#0f172a;--panel:#1e293b;--line:#334155;--text:#f1f5f9;--muted:#94a3b8;--accent:#f97316;--cyan:#38bdf8}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px "Segoe UI","Microsoft YaHei",sans-serif}.bar{height:76px;background:var(--panel);border-bottom:1px solid var(--line);display:flex;align-items:center;gap:12px;padding:0 24px}.brand{color:var(--accent);font-weight:800;letter-spacing:2px;white-space:nowrap}.brand small{display:block;color:#64748b;font-weight:400;letter-spacing:0;font-size:10px;margin-top:6px}input,select,button{height:42px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--text);padding:0 14px}input{min-width:250px;flex:1;letter-spacing:2px}select{width:175px}button{cursor:pointer}button.primary{background:var(--accent);border:0;color:#fff;font-weight:800;letter-spacing:1px;min-width:120px}.shell{display:grid;grid-template-columns:260px 1fr;min-height:calc(100vh - 76px)}aside{background:var(--panel);border-right:1px solid var(--line);padding:18px 0}aside header{display:flex;justify-content:space-between;align-items:center;padding:0 16px 12px;color:var(--muted);font-size:12px;border-bottom:1px solid var(--line)}aside button{height:28px;padding:0 9px;font-size:11px}#history{list-style:none;padding:0;margin:0}.item{padding:14px 16px;border-bottom:1px solid #29374a;cursor:pointer}.item:hover{background:#243044}.number{color:var(--accent);font-family:monospace;font-weight:bold;letter-spacing:2px}.meta{display:flex;justify-content:space-between;color:var(--muted);font-size:11px;margin-top:7px}.note{color:var(--cyan);font-size:11px;margin-top:6px}.actions{display:none;margin-top:9px;gap:6px}.item:hover .actions{display:flex}.actions button{height:24px;font-size:11px;padding:0 7px}main{display:grid;place-items:center;padding:36px}.empty,.result{text-align:center;max-width:760px}.empty h1{letter-spacing:4px;color:#475569}.empty p{line-height:1.8;color:#64748b}.result{background:#1e293b;border:1px solid var(--line);border-radius:12px;padding:32px;width:min(760px,100%)}.result h2{color:var(--accent);letter-spacing:2px;margin:0}.result p{color:var(--muted);line-height:1.7}.route{display:grid;grid-template-columns:1fr auto 1fr;gap:12px;background:#243044;border-radius:8px;padding:16px;text-align:left}.route strong:last-child{text-align:right}.events{list-style:none;text-align:left;padding:0;margin:22px 0 0}.events li{border-left:2px solid var(--line);padding:0 0 16px 14px;margin-left:8px}.events b{display:block}.events small{color:var(--muted)}.error{color:#f87171;min-height:22px}.loading{color:var(--muted)}.spinner{width:30px;height:30px;margin:0 auto 14px;border:3px solid var(--line);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}@media(max-width:760px){.bar{height:auto;min-height:76px;flex-wrap:wrap;padding:14px}.brand{width:100%}.shell{grid-template-columns:1fr}aside{display:none}input{min-width:0}.bar input{width:100%;flex:auto}select{flex:1}.bar button{flex:1}.route{grid-template-columns:1fr;text-align:center}.route strong:last-child{text-align:center}}
</style>
<script>
document.addEventListener('DOMContentLoaded', () => {
  document.querySelector('.empty p').innerHTML='输入集装箱号，自动识别或手动选择承运商。<br>已接入 Maersk、MSC、COSCO；OOCL 将在官网新窗口中手动查询。';
  const request = async (action, data) => { const r = await fetch(`?action=${action}`, {method: data ? 'POST' : 'GET', headers:{'Content-Type':'application/json'}, body:data ? JSON.stringify(data) : undefined}); const j=await r.json(); if(!r.ok) throw Error(j.error||'请求失败'); return j };
  const pause = ms => new Promise(done => setTimeout(done, ms));
  const render = r => { const events=Array.isArray(r.events)?r.events:[]; main.innerHTML=`<section class="result"><h2>${esc(r.container)}</h2><p>${esc(r.carrier)}${r.updated?` · ${esc(r.updated)}`:''}${r.cached?' · 本地缓存':''}</p><p>${esc(r.status||'暂无最新状态')}</p><div class="route"><strong>${esc(r.from_port||'—')}</strong><span>→</span><strong>${esc(r.to_port||'—')}</strong></div><ul class="events">${events.map(e=>{const [name,when='']=String(e.milestone||'').split('\n',2);return `<li><b>${esc(name||'状态更新')}</b><small>${esc(e.loc||'')}${when?' · '+esc(when):''}</small></li>`}).join('')||'<li><small>暂无可显示的运踪节点。</small></li>'}</ul></section>` };
  const run = async () => { const input=$('#container'), no=input.value.trim().toUpperCase(), carrier=$('#carrier').value, manual=['oocl','hapag','one','zim'].includes(carrier)||(carrier==='auto'&&/^(OOLU|OOCU|HLCU|HLXU|ONEU|ZIMU)/.test(no)), popup=manual?window.open('about:blank','_blank'):null; loading(); $('#track').disabled=true; try { const response=await request('track',{container:no,carrier}); if(response.result?.manual_url){ popup ? popup.location.replace(response.result.manual_url) : window.open(response.result.manual_url,'_blank'); renderHistory(response.items); main.innerHTML=`<section class="result" role="status"><h2>${esc(response.result.container)}</h2><p>${esc(response.result.carrier)}</p><p>官方查询页已在新窗口打开；如有要求，请输入箱号或完成验证码后手动查询。</p></section>`; return } let job=response.job; while(job.status!=='done'){ await pause(1000); const status=await request('job&id='+encodeURIComponent(job.id)); job=status.job; if(job.status==='error') throw Error('实时查询失败，请稍后重试。') } popup?.close(); render(job.result); refresh() } catch(error) { popup?.close(); main.innerHTML=`<section class="result"><p class="error" role="alert">⚠ ${esc(error.message)}</p></section>` } finally { $('#track').disabled=false } };
  document.addEventListener('click', event => { if(event.target.closest('#track')){ event.preventDefault(); event.stopImmediatePropagation(); run() } }, true);
  document.addEventListener('keydown', event => { if(event.key==='Enter'&&document.activeElement===$('#container')){ event.preventDefault(); event.stopImmediatePropagation(); run() } }, true);
});
</script>
<body><header class="bar"><div class="brand">🚢 HONSEN AFRICA<small>WMS · LOGISTICS CONSOLE</small></div><label class="sr-only" for="container">集装箱号</label><input id="container" placeholder="MRSU6845613 · 输入集装箱号" autocomplete="off"><label class="sr-only" for="carrier">承运商</label><select id="carrier"><option value="auto">自动识别承运商</option><?php foreach ($carriers as $key => [$name]): ?><option value="<?= htmlspecialchars($key) ?>"><?= htmlspecialchars($name) ?></option><?php endforeach ?></select><button class="primary" id="track">TRACK ▶</button></header><div class="shell"><aside><header>📋 查询历史 <button id="clear">清空</button></header><ul id="history"></ul></aside><main id="main" aria-live="polite"><section class="empty"><div style="font-size:54px">🌍</div><h1>CONTAINER TRACKER</h1><p>输入集装箱号，自动识别或手动选择承运商。<br>已接入 Maersk 与 OOCL，结果直接显示在本页。</p><div class="error" id="error" role="alert"></div></section></main></div>
<script>
const $=s=>document.querySelector(s), main=$('#main');
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(action,data){const r=await fetch(`?action=${action}`,{method:action==='history'?'GET':'POST',headers:{'Content-Type':'application/json'},body:action==='history'?undefined:JSON.stringify(data)}),j=await r.json();if(!r.ok)throw Error(j.error||'请求失败');return j}
function time(v){return new Date(v).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}
function renderHistory(items){$('#history').innerHTML=items.map(x=>`<li class="item" data-no="${esc(x.container)}"><div class="number">${esc(x.container)}</div><div class="meta"><span>${esc(x.carrier)}</span><span>${time(x.time)}</span></div>${x.note?`<div class="note">📝 ${esc(x.note)}</div>`:''}<div class="actions"><button data-note="${esc(x.id)}">备注</button><button data-delete="${esc(x.id)}">删除</button></div></li>`).join('')||'<li class="item" style="color:#64748b;text-align:center">暂无查询记录</li>'}
async function refresh(){renderHistory((await api('history')).items)}
async function post(action,data){const j=await api(action,data);renderHistory(j.items);return j}
function loading(){main.innerHTML='<section class="result loading" role="status"><div class="spinner"></div><h2>正在提取运踪数据</h2><p>正在连接承运商系统并解析路线与节点，首次查询约需 10–20 秒。</p></section>'}
async function track(){const no=$('#container').value.trim().toUpperCase(),carrier=$('#carrier').value,manual=['oocl','hapag','one','zim'].includes(carrier)||(carrier==='auto'&&/^(OOLU|OOCU|HLCU|HLXU|ONEU|ZIMU)/.test(no)),popup=manual?window.open('about:blank','_blank'):null;loading();$('#track').disabled=true;try{const j=await post('track',{container:no,carrier}),r=j.result;if(r.manual_url){if(popup)popup.location.replace(r.manual_url);else window.open(r.manual_url,'_blank');main.innerHTML=`<section class="result" role="status"><h2>${esc(r.container)}</h2><p>${esc(r.carrier)}</p><p>官方查询页已在新窗口打开；如有要求，请输入箱号或完成验证码后手动查询。</p></section>`;return}popup?.close();const events=Array.isArray(r.events)?r.events:[];main.innerHTML=`<section class="result"><h2>${esc(r.container)}</h2><p>${esc(r.carrier)}${r.updated?` · ${esc(r.updated)}`:''}${r.cached?' · 本地缓存':''}</p><p>${esc(r.status||'暂无最新状态')}</p><div class="route"><strong>${esc(r.from_port||'—')}</strong><span>→</span><strong>${esc(r.to_port||'—')}</strong></div><ul class="events">${events.map(e=>{const [name,when='']=String(e.milestone||'').split('\n',2);return `<li><b>${esc(name||'状态更新')}</b><small>${esc(e.loc||'')}${when?' · '+esc(when):''}</small></li>`}).join('')||'<li><small>暂无可显示的运踪节点。</small></li>'}</ul></section>`}catch(e){popup?.close();main.innerHTML=`<section class="result"><p class="error" role="alert">⚠ ${esc(e.message)}</p></section>`}finally{$('#track').disabled=false}}
$('#track').onclick=track; $('#container').onkeydown=e=>e.key==='Enter'&&track(); document.addEventListener('keydown',async e=>{const input=$('#container'),key=e.key.toLowerCase(),modifier=e.ctrlKey||e.metaKey;if(modifier&&key==='a'&&document.activeElement!==input){e.preventDefault();input.focus();input.select();return}if(modifier&&key==='v'&&document.activeElement!==input){e.preventDefault();try{input.value=await navigator.clipboard.readText();input.focus()}catch{}}}); $('#clear').onclick=()=>confirm('确定清空所有查询历史？')&&post('clear',{}); $('#history').onclick=async e=>{let b=e.target;if(b.dataset.note){const item=b.closest('.item'),note=prompt('备注',item.querySelector('.note')?.textContent.replace('📝 ','')||'');if(note!==null)await post('note',{id:b.dataset.note,note});return}if(b.dataset.delete){await post('delete',{id:b.dataset.delete});return}const item=b.closest('.item');if(item){$('#container').value=item.dataset.no;track()}};refresh();
</script></body></html>
