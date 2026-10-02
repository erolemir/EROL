# EROL

**Extensible Reasoning & Orchestration Layer**

Codex ve Claude Code için ortak proje hafızası, ilgili skill seçimi, kontrollü
otonom görev yürütme ve kaynaklı araştırma katmanı.

EROL, geliştirme asistanının önceki doğrulanmış çözümleri kullanmasını, göreve
uygun iş akışlarını seçmesini ve sonucu testlerle ve ayrı bir incelemeyle
değerlendirmesini sağlar. Teknik, ürün, pazar ve rakip araştırması da desteklenir.
Python çekirdeğinin üçüncü taraf runtime bağımlılığı yoktur.

English: EROL provides shared project memory, specialist workflows, opt-in task
execution and evidence-driven research for Codex and Claude Code. Installation
commands and CLI names below work independently of the documentation language.

**Dağıtım:** Test edilmiş paketler [GitHub Releases](https://github.com/erolemir/EROL/releases)
ve `stable` dalından dağıtılır. `main` geliştirme kaynağıdır; sürüm numarası `stable`
ile farklı olabilir. EROL şu anda npm veya PyPI kayıtlarında yayımlanmıyor.
`npm install -g erol` veya `pip install erol-ai` yerine aşağıdaki GitHub kurulumunu kullan.

## İçindekiler

- [Hangi kurulumu seçmeliyim?](#hangi-kurulumu-seçmeliyim)
- [Gereksinimler](#gereksinimler)
- [Codex eklentisi](#codex-eklentisi)
- [Claude Code eklentisi](#claude-code-eklentisi)
- [Windows: bilgisayar genelinde erol komutu](#windows-bilgisayar-genelinde-erol-komutu)
- [macOS ve Linux: Python CLI](#macos-ve-linux-python-cli)
- [Kaynak koddan kullanım ve proje kurulumu](#kaynak-koddan-kullanım-ve-proje-kurulumu)
- [Günlük kullanım](#günlük-kullanım)
- [Otonom geliştirme görevi](#otonom-geliştirme-görevi)
- [Teknik, ürün ve rakip araştırması](#teknik-ürün-ve-rakip-araştırması)
- [Görev keşfi, kuyruk ve paralel inceleme](#görev-keşfi-kuyruk-ve-paralel-inceleme)
- [Hafıza ve öğrenme](#hafıza-ve-öğrenme)
- [Güncelleme ve kaldırma](#güncelleme-ve-kaldırma)
- [Sorun giderme](#sorun-giderme)
- [Doğrulama ve geliştirme](#doğrulama-ve-geliştirme)
- [Yetenekler ve sınırlar](#yetenekler-ve-sınırlar)

## Hangi kurulumu seçmeliyim?

| İhtiyaç | Kurulum | Kullanım |
| --- | --- | --- |
| Codex sohbetlerinde EROL kullanmak | Codex eklentisi | Desktop'ta EROL seçimi; CLI/IDE'de `$erol` |
| Claude Code oturumlarında kullanmak | Claude eklentisi | `/erol:erol` |
| Terminalden plan, görev, araştırma ve panel çalıştırmak | Python CLI | `erol ...` |
| EROL'u geliştirmek veya projeye özel bridge kurmak | Kaynak checkout'u | `npx --no-install erol ...` veya editable Python kurulumu |

Birden fazla yolu birlikte kullanabilirsin. Eklenti kendi runtime'ını içerir;
ayrıca Python paketini kurmak gerekmez. **Eklenti kurulumu, terminale global `erol`
komutu eklemez.** Bunun için CLI bölümünü takip et.

Eklenti ve `plan` komutu bağlam/öneri sağlar; işi sohbetin asistanı yürütür.
`run` ve açık politika ile `queue work` ise EROL'un görev yürütücüsünü başlatır.

## Gereksinimler

| Bileşen | Gereksinim |
| --- | --- |
| Python | 3.11 veya üzeri; hem CLI hem eklentinin çalıştığı bilgisayarda |
| Node.js | Eklentinin Node başlatıcısı ve Node CLI için 18 veya üzeri |
| Git | Git marketplace kurulumu ve worktree ile otonom görevler için |
| Codex / Claude Code | Kullanacağın altyapının CLI'si ve geçerli giriş/erişim |
| İnternet | İlk indirme, model çağrıları ve web araştırması için |

Python-only CLI Node gerektirmez. Kontrol komutlarının çalıştıracağı test araçları
ve proje bağımlılıkları ayrıca senin projenin ortamında bulunmalıdır.

Windows PowerShell'de ön kontrol:

```powershell
py -3 --version
node --version
git --version
codex --version
claude --version
```

Kullanmayacağın altyapının komutunu çalıştırman gerekmez. macOS/Linux'ta Python
kontrolü için `python3 --version` kullan. Eksik araçların resmi kurulumları:
[Python](https://www.python.org/downloads/), [Node.js](https://nodejs.org/en/download),
[Git](https://git-scm.com/downloads), [Codex](https://developers.openai.com/codex/cli),
[Claude Code](https://code.claude.com/docs/en/setup).

## Codex eklentisi

Terminalde test edilmiş release kanalını kaydet ve eklentiyi kur:

```console
codex plugin marketplace add erolemir/EROL --ref stable
codex plugin add erol@erol
codex plugin list --marketplace erol --json
```

Listede `installed: true`, `enabled: true` ve kurulu sürümü görmelisin.
Sonra çalışma projen içinde **yeni bir Codex sohbeti** aç. Desktop'ta `@` menüsünden
EROL'u seç; görünmüyorsa uygulamayı yeniden aç. Örnek görev:

```text
@EROL Bu projeyi incele, geçmiş kararları dikkate al, hatayı düzelt ve test et.
```

Codex CLI/IDE skill seçimi `$erol` veya `/skills` üzerinden yapılır:

```text
$erol API hatasını incele, uygun iş akışını seç ve sonucu testlerle doğrula.
```

Desktop picker'ın görünümü istemci sürümüne bağlıdır; eklentinin kurulu/etkin
olmasıyla canlı picker/model kabulü ayrı kontrollerdir.
[Resmi marketplace belgesi](https://developers.openai.com/plugins/build/plugins)
ve [EROL eklenti ayrıntıları](docs/plugin.md).

## Claude Code eklentisi

Kullanıcı kapsamında kurulum tüm yerel projelerin için geçerlidir:

```console
claude plugin marketplace add https://github.com/erolemir/EROL.git#stable
claude plugin install erol@erol --scope user
claude plugin list
```

Listede `erol@erol`, sürüm ve `enabled` durumunu kontrol et. Projende yeni bir
Claude Code oturumu aç ve tam skill adıyla başla:

```text
/erol:erol Bu ürünü Türkiye'deki küçük işletmeler için değerlendir; pazar araştırması ve rakip analizi yap, güncel kaynakları göster.
```

Kısa `/erol` adı, istemci destekliyorsa ve başka skill ile çakışmıyorsa kullanılabilir.
Giriş hatası varsa Claude Code içinde `/login` ile girişini yenile. Eklenti kurulumu
model hesabı veya abonelik oluşturmaz.
[Resmi kurulum belgesi](https://code.claude.com/docs/en/plugins/install) ve
[skill adlandırma kuralları](https://code.claude.com/docs/en/skills#how-a-skill-gets-its-command-name).

## Windows: bilgisayar genelinde erol komutu

Bu yol ayrı bir Python ortamı kurar; başka projelerin Python paketlerine dokunmaz.
PowerShell'de sırayla çalıştır. `0.1.6` tekrarlanabilir bir örnek sürümdür;
[Releases sayfasındaki](https://github.com/erolemir/EROL/releases) istediğin sürüme
göre `$erolVersion` değerini değiştirebilirsin.

### 1. Paketi indir ve SHA256 değerini doğrula

```powershell
$erolVersion = '0.1.6'
$erolDownloadDir = Join-Path $env:USERPROFILE ".erol\downloads\$erolVersion"
$erolWheelName = "erol_ai-$erolVersion-py3-none-any.whl"
$erolReleaseUrl = "https://github.com/erolemir/EROL/releases/download/v$erolVersion"
New-Item -ItemType Directory -Path $erolDownloadDir -Force | Out-Null
Invoke-WebRequest "$erolReleaseUrl/$erolWheelName" -OutFile (Join-Path $erolDownloadDir $erolWheelName)
Invoke-WebRequest "$erolReleaseUrl/SHA256SUMS" -OutFile (Join-Path $erolDownloadDir 'SHA256SUMS')
$erolHashLine = (Select-String -LiteralPath (Join-Path $erolDownloadDir 'SHA256SUMS') -SimpleMatch "  $erolWheelName").Line
if (-not $erolHashLine) { throw 'SHA256SUMS içinde wheel kaydı bulunamadı' }
$erolExpectedHash = ($erolHashLine -split '\s+')[0]
$erolActualHash = (Get-FileHash -LiteralPath (Join-Path $erolDownloadDir $erolWheelName) -Algorithm SHA256).Hash.ToLowerInvariant()
if ($erolActualHash -ne $erolExpectedHash) { throw 'EROL paketinin SHA256 değeri eşleşmiyor' }
```

### 2. Ayrı Python ortamına kur

```powershell
$erolCliDir = Join-Path $env:USERPROFILE ".erol\cli\$erolVersion"
py -3 -m venv $erolCliDir
& (Join-Path $erolCliDir 'Scripts\python.exe') -m pip install --no-index --no-deps (Join-Path $erolDownloadDir $erolWheelName)
& (Join-Path $erolCliDir 'Scripts\erol.exe') --version
```

Son komut seçtiğin sürümü göstermeli. Ortamı aktive etmek gerekmez; PowerShell
execution policy değiştirilmez. `py -3` Python 3.11+ seçmelidir; birden fazla sürüm
kuruluysa örneğin `py -3.12` ile ortamı oluşturabilirsin.

### 3. Her klasörden erol komutuyla eriş

Python'un oluşturduğu native başlatıcıyı kullanıcı komut dizinine kopyala:

```powershell
$erolUserBin = Join-Path $env:USERPROFILE '.local\bin'
New-Item -ItemType Directory -Path $erolUserBin -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $erolCliDir 'Scripts\erol.exe') -Destination (Join-Path $erolUserBin 'erol.exe') -Force
$erolUserPath = [string][Environment]::GetEnvironmentVariable('Path', 'User')
if ($erolUserPath.Split(';') -notcontains $erolUserBin) {
    [Environment]::SetEnvironmentVariable('Path', "$erolUserPath;$erolUserBin", 'User')
}
if ($env:Path.Split(';') -notcontains $erolUserBin) { $env:Path += ";$erolUserBin" }
erol --version
```

Kopyalanan başlatıcı bu Python ortamına bağlıdır; `$erolCliDir` dizinini taşıma veya
silme. Güncellemede yeni sürümü kurup başlatıcıyı yeniden kopyala. PATH değişikliğini
açık uygulamaların görmesi için yeni terminal açmak veya uygulamayı yeniden açmak
gerekebilir. Kurulum kullanıcı hesabın kapsamındadır; yönetici ve sistem PATH
değişikliği gerekmez. Mevcut başka bir `erol.exe` varsa kopyalamadan önce sahipliğini incele.

## macOS ve Linux: Python CLI

Python 3.11+ ile ayrı ortam oluştur. `0.1.6` örneğini istediğin release'e uyarlayabilirsin:

```sh
python3 -m venv "$HOME/.local/share/erol/venv"
"$HOME/.local/share/erol/venv/bin/python" -m pip install --no-deps \
  https://github.com/erolemir/EROL/releases/download/v0.1.6/erol_ai-0.1.6-py3-none-any.whl
"$HOME/.local/share/erol/venv/bin/erol" --version
```

Paket hash'ini release'in `SHA256SUMS` dosyasıyla karşılaştırabilirsin; macOS'ta
`shasum -a 256`, Linux'ta `sha256sum` kullanılabilir. Tam başlatıcı yoluyla her
projeden çalıştırabilir veya ortamı mevcut terminalde aktive edebilirsin:

```sh
. "$HOME/.local/share/erol/venv/bin/activate"
erol --version
```

Aktivasyon açık terminal için geçerlidir. EROL'u hedef projenin virtualenv'inden ayrı tut.

## Kaynak koddan kullanım ve proje kurulumu

Test edilmiş kanalın checkout'u için:

```console
git clone --branch stable https://github.com/erolemir/EROL.git
cd EROL
npm install --ignore-scripts --no-audit --no-fund
npx --no-install erol --version
npx --no-install erol --project /path/to/project status
```

Windows'ta proje yolunu örneğin `"C:\Projeler\BenimProjem"` olarak yaz.
`npx --no-install` checkout'taki komutu kullanır; registry'den aynı adlı başka bir
paketi indirmez. Node CLI'nin runtime bağımlılığı/install hook'u yoktur. Node yanlış
Python seçiyorsa executable yolunu belirt; Windows örneği:

```powershell
$env:EROL_PYTHON = 'C:\Program Files\Python312\python.exe'
```

Python geliştirme kurulumu seçtiğin virtualenv içinde `python -m pip install -e .`
ile yapılabilir. Editable kurulum checkout'a bağlıdır; wheel kurulumu değildir.

### İsteğe bağlı projeye özel bridge

Native eklenti kullanıyorsan ayrıca bridge zorunlu değildir. Önce önizle:

```console
erol --project /path/to/project setup --harness codex
erol --project /path/to/project setup --harness codex --apply
erol --project /path/to/project setup --harness claude --apply
```

`--apply`, Codex için `.agents/skills/erol/SKILL.md` ve `AGENTS.md`; Claude için
`.claude/skills/erol/SKILL.md` ve `CLAUDE.md` üzerindeki sahip olunan bloğu yönetir.
Mevcut talimatlar korunur, değişiklikler yedeklenir, sahiplik çakışmaları reddedilir.
Ekibin için kullanmadan önce normal diff incelemesi yap. Node bridge başlatıcının
mutlak yolunu kaydeder; checkout taşınırsa setup'ı yeniden çalıştır. Python bridge,
harness ortamında `erol` komutunun erişilebilir olmasını gerektirir.
[Kurulum/sahiplik ayrıntıları](docs/installation.md).

## Günlük kullanım

Terminali kendi projenin klasöründe aç. Windows örneği:

```powershell
Set-Location 'C:\Projeler\BenimProjem'
erol --version
erol status
erol doctor
erol plan --task 'API hatasını düzelt, regresyon testleri ve code review hazırla'
erol explain --task 'Küçük işletmeler için pazar araştırması ve rakip analizi hazırla'
erol skills list --category backend
erol skills list --category growth
erol skill show --name market-research
erol memory search 'veritabanı zaman aşımı' --mode hybrid
erol runs list
erol panel --open
```

`status` proje kimliği/sürüm/hafızayı gösterir. `doctor` paket/ortam kontrolüdür;
model girişinin veya görevin geçtiği anlamına gelmez. `plan` öneriyi, `explain`
seçim gerekçesini verir. `panel` yerel görev/kuyruk/kanıt kayıtlarını gösterir;
terminalde Ctrl+C ile kapanır.

Başka klasörden `--project`, farklı harici hafıza için `--home` kullan.
**Bu seçenekler alt komuttan önce gelmelidir:**

```powershell
erol --project 'C:\Projeler\BenimProjem' status
erol --project 'C:\Projeler\BenimProjem' --home 'D:\EROL-Hafiza' runs list
```

`RUN_ID`, `JOB_ID` gibi değerleri sonuçtaki gerçek kimlikle değiştir.
Boşluk/Türkçe karakter içeren dosya yollarını tırnak içine al.

## Otonom geliştirme görevi

### 1. Projeyi ve kabul kontrollerini hazırla

Yerel Git repository, HEAD commit'i ve temiz çalışma ağacı gerekir. Önce `git status`
ile kontrol et. Test araçları/proje bağımlılıkları kontrollerin executable ortamında
kurulu olmalıdır. Projede `checks.json` oluştur. **Python unittest kullanan bir proje**:

```json
{
  "schema_version": 1,
  "checks": [
    {
      "name": "acceptance-tests",
      "kind": "acceptance",
      "argv": ["python", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
      "timeout_seconds": 300
    }
  ]
}
```

Kendi test sistemine göre değiştir. `unittest discover` test bulamasa bile başarılı
çıkabilir; ilgili testlerin bulunduğunu ve hedef hatayı yakaladığını önce elle doğrula.
Her kontrolde `name`, `kind`, literal `argv` ve 1..300 saniye `timeout_seconds`
bulunur. En az bir `acceptance` zorunludur; `static` lint/type kontrolü tek başına
görevi tamamlayamaz.

Komutlar shell yorumlaması olmadan worktree içinde çalışır. `&&`, pipe veya tüm
komutu tek string olarak yazma. `python` yanlış ortamı seçiyorsa `argv[0]` için
kurulu Python'un mutlak yolunu kullan. Windows'ta `.cmd/.bat/.ps1` wrapper yerine
native executable kullan: Node testi için `["node", "--test", "tests/add.test.mjs"]`.
Kontrol dosyasını projeye koyduysan inceleyip commit et; yeni dosya ağacı kirletir.
[Şema](schemas/checks.schema.json) ve [örnek](examples/checks.json).

### 2. Görevi çalıştır

```powershell
erol run --task 'Belirtilen API hatasını düzelt ve ilgili testleri geçir' --harness codex --checks '.\checks.json'
```

Claude uygulaması için `--harness claude`; Codex uygulaması/Claude incelemesi için
`--review-harness claude`; iki/üç inceleyici için `--reviewers 2` veya `--reviewers 3`.
Varsayılan aynı altyapıda ayrı inceleme oturumudur. İsteğe bağlı `--task-id` yeni ve
benzersiz olmalıdır; tekrar kullanılmış ID reddedilir.

Başlangıç kontrolleri kaydedilir; uygulama ayrı worktree'de yapılır, kontroller
çalıştırılır ve ayrı oturumda incelenir. Tamamlanma aynı değişiklik digest'inde
başarılı kabul kontrolleri ve açık kritik/yüksek bulgu bulunmamasını gerektirir.
Bir projede bir implementer çalışır; inceleyicilere düzenleme araçları verilmez.

Varsayılan görev süresi 60 dakika, model oturumu 15 dakika, kontrol başına en fazla
5 dakikadır. İlk uygulamadan sonra en fazla iki düzeltme turu vardır; tekrarlanan
başarısız strateji yeniden planlama ister. Sınırda `needs_attention` ile çalışma
korunur. Mevcut CLI model ayarı kullanılır; EROL model adı atamaz. Eksik yetenek,
izin veya giriş raporlanır; başka altyapıya sessizce geçilmez.

### 3. İncele, devam ettir veya iptal et

```powershell
erol runs list
erol runs show --id RUN_ID
erol runs resume --id RUN_ID
erol runs cancel --id RUN_ID
```

Sonuç worktree yolu, patch, gözlenen kontroller ve inceleme raporunu içerir.
Verilen worktree'de normal Git diff ile değişiklikleri incele. `run` otomatik merge,
push/yayın yapmaz; teslim kararını sana bırakır.

`resume` proje/worktree/kontrol tanımı ve süreç durumunu doğrular. Çalışan/belirsiz
oturum varken ikinci worker açılmaz. Değişiklikler değişmişse eski test/inceleme
kanıtları geçersizleşir. Tamamlanan/iptal edilen görev yeni görev gibi resume
edilmez. `cancel` kalıcı taleptir; kayıtlar/worktree korunur.
[Yürütme sözleşmesi ve platform sınırları](docs/execution.md).

## Teknik, ürün ve rakip araştırması

Sohbette EROL'u seçip araştırma isteği verebilirsin. Karar, ürün, coğrafya, hedef
müşteri ve ölçütleri belirt:

```text
Teknik: SQLite ve PostgreSQL'i yerel/offline uygulama için karşılaştır.
Veri bütünlüğü, eşzamanlı yazma, bakım ve dağıtımı resmi kaynaklarla değerlendir.

Ürün/rakip: Türkiye'deki küçük işletmeler için ürünümüzü A ve B ile karşılaştır.
Güncel fiyat, özellik sınırları, hedef müşteri ve geçiş maliyetlerini kaynaklandır.
Doğrulanmış bilgileri çıkarımlardan ayır; erişilemeyen/çelişen bilgileri belirt.
```

Yürütücü ile kalıcı araştırma çıktısı için:

```powershell
erol run --mode research --task 'SQLite ve PostgreSQL için resmi kaynaklarla yerel uygulama karar raporu hazırla' --harness codex --checks '.\research-checks.json'
```

Temiz Git projesi ve soruya özel anlamlı kabul kontrolleri yine gerekir. Ayrı,
commit edilmiş araştırma brief'i olan küçük bir Git repository de yeterlidir.
`research-checks.json` hazır gelen bir dosya değildir; kriterlerini test eden
komutları tanımlamalıdır. SQLite/PostgreSQL sorusu için hedef projede
`scripts/check_research.py` adlı **kapsam kontrolü** örneği:

```python
import json
from pathlib import Path
from urllib.parse import urlsplit

report = Path("research/report.md").read_text("utf-8").casefold()
ledger = json.loads(Path("research/sources.json").read_text("utf-8"))
assert "sqlite" in report and "postgresql" in report
assert any(term in report for term in ("concurrency", "eşzaman", "es zaman"))
assert ledger["claims"] and ledger["limitations"]
hosts = {urlsplit(source["url"]).hostname for source in ledger["sources"]}
assert hosts & {"sqlite.org", "www.sqlite.org"}
assert hosts & {"postgresql.org", "www.postgresql.org"}
```

Bu script'i çağıran `research-checks.json`:

```json
{
  "schema_version": 1,
  "checks": [
    {"name": "research-scope", "kind": "acceptance",
     "argv": ["python", "-B", "scripts/check_research.py"], "timeout_seconds": 60}
  ]
}
```

Script/dosyaları oluşturup commit et; ürün/rakip sorusu için beklenen ürün/kriterlere
göre değiştir. Bu kontrol kapsamı doğrular; kelime veya kaynak sayısı olgusal
doğruluk kanıtı değildir.

Çıktılar worktree'de `research/report.md` ve `research/sources.json` olur: kaynak
bağlantıları, iddialar, erişim tarihleri, çelişkiler ve belirsizlikler. EROL public
HTTPS erişimlerini zaman/HTTP/hash/byte bilgisiyle ayrıca gözler; gövdeleri arşivlemez.
Ayrı inceleyici kaynak/iddiaları karşılaştırır. Erişilemeyen/çelişen kaynak veya
eksik inceleme tamamlanmayı engeller. Erişim receipt'i kaynak doğruluğu/platform
imzası değildir; model incelemesi de yanılabilir. Native web erişimi CLI izinlerine bağlıdır.
[Araştırma sözleşmesi](docs/research-execution.md), [ledger şeması](schemas/research.schema.json),
[sentetik format](examples/research-sources.json).

## Görev keşfi, kuyruk ve paralel inceleme

`scan` TODO/içe alınmış issue'ları keşfeder. **`scan --checks` verdiğinde kontrol
komutları kaynak projede gerçekten çalışır.** Yalnızca incelemiş olduğun komut
dosyasını ver. Kuyruk açık proje politikası gerektirir:

```powershell
$erolChecks = (Resolve-Path '.\checks.json').Path
$erolPolicy = Join-Path $env:USERPROFILE '.erol\policies\benim-projem.json'
New-Item -ItemType Directory -Path (Split-Path $erolPolicy) -Force | Out-Null
erol scan --checks $erolChecks
erol queue policy --harness codex --checks $erolChecks --output $erolPolicy --max-tasks 2 --reviewers 2
# Oluşturulan politikayı incele; sonra:
erol queue enqueue --policy $erolPolicy
erol queue list
erol queue work --policy $erolPolicy
```

Varsayılan kural kontrol hatalarını eşleştirir; her TODO'nun otomatik çalışacağını
varsayma. Politika proje kimliği, kontrol digest'i, kural ve kaynak sınırlarını bağlar.
Arka planda sürekli çalışan bir daemon yoktur.

```console
erol queue depend --id CHILD_JOB --on PARENT_JOB
erol queue resume --id JOB_ID --policy /absolute/policy.json
erol queue cancel --id JOB_ID
```

Bağımlılıklar döngüsüzdür; doğrulanmış üst görev patch'leri child worktree'ye
uygulanır. Çakışmalar dikkat gerektirir. Paralellik read-only incelemededir; aynı
projede eşzamanlı yazan implementer'lar yoktur. [Politika/kurtarma sözleşmesi](docs/autonomous-work.md).

Davranış ölçümü açık sentetik fixture ve gerçek CLI oturumları gerektirir:

```console
erol benchmark --suite examples/behavior-suite.json --harness codex --report /absolute/behavior-report.json
erol panel --port 8765 --open
```

Suite yolunu checkout'taki [örneğe](examples/behavior-suite.json) veya kendi suite'ine
yönelt. Benchmark model çağrısı yapar; süre/kullanım tüketir. Aynı fixture'ı EROL
bağlamıyla/bağlam olmadan karşılaştırır; iki kolda runner kontrolleri/inceleme korunur.
Bu context ablation'dır; saf harness karşılaştırması değildir. Tek pair genel hız/token
kazancı göstermez. Panel yalnızca 127.0.0.1 üzerinde seçilmiş read-only kanıtları
gösterir; görev başlatmaz, raw sohbet/credentials sunmaz.

## Hafıza ve öğrenme

Hafıza proje/eklenti dizininin dışında tutulur:

```text
Windows: %USERPROFILE%\.erol\state\<proje-kimliği>\memory.db
macOS/Linux: ~/.erol/state/<proje-kimliği>/memory.db
Ek kayıtlar: runs.db, work.db ve yeniden oluşturulabilen search.db
```

Kimlik credential içermeyen Git remote'undan, remote yoksa canonical kök yoldan
üretilir. Aynı proje kimliği ve `--home` kullanan Codex/Claude hafızayı paylaşır.
`--home` repository dışında olmalıdır. SQLite esastır; Markdown export okunabilir
görünümdür. EROL raw konuşma/credentials kopyalamaz; transcript upload/telemetri
uygulanmaz. Model çağrıları seçilen sağlayıcının politikalarına tabidir.

```console
erol memory status
erol memory index
erol memory search "veritabanı zaman aşımı" --mode hybrid --max-chars 6000
erol memory search "database timeout" --mode lexical
erol memory export
erol learning status
erol learning candidates
```

Öğrenme zinciri:

```text
incident → tekrar eden pattern → candidate → eval → proje skill'i
         → gerçek görevde doğrulanmış kullanım → kontrollü promotion
```

Doğrulanmış onarım/ayrı incelemeden sonra temizlenmiş kanıtı
[incident formatına](examples/incident.json) göre kaydet:

```console
erol incident record --input /path/to/reviewed-incident.json
erol incident match --component contact-import --exception ImportCursorError --error "ImportCursorError skipped rows"
erol learning candidates
erol learning eval --id CANDIDATE_ID --input /path/to/reviewed-behavior-eval.json
erol learning activate --id CANDIDATE_ID
erol plan --task-id UNIQUE_TASK_ID --task "Güncel geliştirme görevi"
erol skill usage --task-id UNIQUE_TASK_ID --input /path/to/reviewed-completion.json
erol skill metrics --name SKILL_NAME
erol learning promotion --name SKILL_NAME
```

Varsayılan üç farklı doğrulanmış görev, tutarlı neden/çözüm ve kalite kapıları
proje adayı oluşturur. Aynı task/incident'i tekrar oynatmak kanıt sayısını artırmaz.
Aktivasyon olumlu/olumsuz trigger, davranış, güvenlik ve bağlam bütçesi incelemesi
ister. Kullanım kredisi aynı tam revision digest'i yeni görevin bağlamına gerçekten
alındıysa verilir. Başarısız/yanlış kullanım revision'ı yönlendirmeden çıkarır.
Global yükseltme açık onay/cross-project kanıt ister; otomatik global skill kurulumu
uygulanmaz. Örnek JSON'lar sentetik formatlardır; gerçek onarım kanıtı değildir.
[Öğrenme döngüsü](docs/learning.md), [eval sözleşmeleri](docs/eval-plan.md).

## Güncelleme ve kaldırma

### Native eklentileri güncelle

```console
codex plugin marketplace upgrade erol
codex plugin add erol@erol
claude plugin marketplace update erol
claude plugin update erol@erol
```

Yeni/reload edilmiş oturumda güncel sürümü kullan. `stable` hareketli kanaldır;
sabit `vX.Y.Z` ref'i o sürümde kalır. Yerel-path marketplace GitHub'dan kendiliğinden
güncellenmez. Yerel `erol` marketplace varsa yalnızca o kaynağı native kaldırma
komutuyla kaldırıp Git kaynağını ekle; Claude'da plugin'i tekrar kur.

Claude otomatik güncellemesi: `/plugin` → Marketplaces → erol → auto-update.
Windows'ta isteğe bağlı scheduled native refresh, EROL checkout'undan:

```powershell
./scripts/update-plugins.ps1 -Harness Both -Register
./scripts/update-plugins.ps1 -Harness Both
./scripts/update-plugins.ps1 -Unregister
```

Görev login'de ve kullanıcı oturum açmışken altı saatte bir çalışır; her bilgisayarda
ayrı kurulmalıdır. CLI wheel ortamını güncellemez. Updater `~/.erol/updater` içindedir.
[Release/updater sınırları](docs/releases.md).

### CLI'yi güncelle veya kaldır

Windows'ta yeni `$erolVersion` ile wheel/SHA256/venv adımlarını tekrarla; global
başlatıcıyı yeniden kopyala. macOS/Linux'ta ortamın Python'uyla yeni release
wheel'ini `-m pip install --upgrade --no-deps <WHEEL_URL_OR_PATH>` ile kur.
Placeholder yerine seçtiğin asset'in URL/yolunu yaz.

Native plugin kaldırma:

```console
codex plugin remove erol@erol
claude plugin uninstall erol@erol
```

Projeye özel bridge kaldırma önce önizlenir:

```console
erol --project /path/to/project uninstall --harness codex
erol --project /path/to/project uninstall --harness codex --apply
erol --project /path/to/project uninstall --harness claude --apply
```

CLI için kurduğun ortamın Python'uyla `-m pip uninstall erol-ai` çalıştır;
Windows global kopyasını da kaldır. Canonical hafıza uninstall'da korunur.
Bütün `~/.erol` dizinini silme; hafıza/korunmuş worktree'ler aynı home altında olabilir.

## Sorun giderme

| Belirti | Kontrol / çözüm |
| --- | --- |
| `erol` tanınmıyor | Eklenti global CLI sağlamaz. CLI'yi kur; tam venv executable yolunu dene. Windows kullanıcı `.local\bin` PATH'ini/yeni terminali kontrol et. |
| Python yetersiz | `py -3 --version` / `python3 --version`; 3.11+ kullan. Node'da `EROL_PYTHON` executable yolunu belirt. |
| Skill görünmüyor | Plugin listesinde etkinlik/sürümü kontrol et; yeni oturum/restart. Claude'da `/erol:erol`, Codex CLI'de `$erol`. |
| Claude OAuth expired / HTTP 401 | Claude Code içinde `/login`; sonra tekrar dene. EROL credentials kopyalamaz/giriş atlatmaz. |
| Codex girişi yok | Native `codex login` akışını tamamla; EROL öncesi native CLI'yi kontrol et. |
| `clean Git working tree` | `git status` ile tracked/untracked değişiklikleri incele; gereken dosyaları normal workflow ile commit et. |
| Check executable bulunamadı | Test ortamı/bağımlılıkları kur; `argv[0]` için mutlak executable veya uygun PATH kullan. |
| Shell wrapper / pipe reddi | `argv` ayrı argüman listesi olsun; native Python/Node executable kullan. |
| `needs_attention` | `runs show` ile kontrol/inceleme/süre nedenini oku; sebebi çözüp uygun durumda `runs resume`. |
| Worker / belirsiz süreç | İkinci worker başlatma; ilgili native oturum/süreci doğrula, cancel/resume araçlarını kullan. |
| Skill seçilmiyor | `explain`, `skills list`, `skill show`; açık ifade eşlemesi her paraphrase'i anlamaz. |
| Node → Python spawn reddi | Plugin'de aynı izinlerle bundled direct Python yolu vardır; host izinlerini atlatma. Kurulum belgesine bak. |
| Panel portu dolu | `erol panel --port 8766 --open`; sunucuyu Ctrl+C ile kapat. |

Ortam/eklenti kontrolünün geçmesi canlı model görevinin geçtiği anlamına gelmez.
Model çağrıları sağlayıcı süre/kullanım limitlerine tabidir.

## Doğrulama ve geliştirme

Kaynak checkout'unda, geliştirme virtualenv'i ile tam kontrol sırası:

```console
python -m pip install -e . -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check src tests scripts bin
ruff format --check src tests scripts bin
mypy --explicit-package-bases src/erol bin/erol.py
npm test
python scripts/check_adapter_drift.py --check
python scripts/validate.py
python -m build
python scripts/package_smoke.py
npm pack --pack-destination dist
python scripts/npm_package_smoke.py
```

Node testleri için önce `npm install --ignore-scripts --no-audit --no-fund`.
`erol eval` deterministic routing/pack kontrolüdür; canlı model/araştırma başarısı değildir.

`v0.1.6` için [tam main CI matrisi](https://github.com/erolemir/EROL/actions/runs/37073828803)
Linux/macOS/Windows, Python 3.11/3.14 işlerinin hepsini geçti. Suite 183 Python ve
12 Node testi içerir; Windows'ta bir POSIX permission testi atlanır.
[Release workflow](https://github.com/erolemir/EROL/actions/runs/37074391455) sürümlü
paketleri tekrar üretip sınadı. `RELEASE.json` source commit'i, `SHA256SUMS` üç
arşivin hash'ini içerir. [Yerel/live kayıtlar](docs/validation.md).

## Yetenekler ve sınırlar

- 96 hazır skill, 18 advisory rol: backend, frontend, coding, security, DevOps,
  SEO, marketing, growth, data/AI. [Tam katalog](docs/skill-catalog.md).
- Türkçe/ASCII Türkçe açık trigger/alias ile desteklenir. Hafıza BM25 ve bilingual
  kavram eşlemesi kullanır; neural embedding uygulanmaz.
- Kullanım kanıtı tam revision'a/bağlama alınmış benzersiz göreve bağlıdır. Hafıza
  geçmiş referanstır; güncel kodla çelişirse kod esas alınır.
- Opt-in yürütme bir projede bir implementer, sınırlı kuyruk ve paralel read-only
  review sağlar. Keşif genel amaçlı bağımsız karar/daemon değildir.
- Worktree OS sandbox'ı değildir. Native CLI izinleri ve Windows/POSIX process
  cleanup kendi sınırlarına sahiptir. Lint/agent mesajı tek başına başarı veya
  containment kanıtı değildir.
- Live Codex onarım/resume, kuyruk+paralel review, kaynak erişimi ve bir pair ölçüldü.
  Claude fake-protocol testleri geçse de expired-OAuth sonrası canlı testler kullanıcı
  isteğiyle atlandı. Desktop picker canlı kabulü ayrı bir adımdır.
- CI deterministic test/paket kapsamıdır; her platformda live Codex/Claude veya
  geniş ürün/rakip araştırması doğruluğu iddiası değildir.
- Genel hız/başarı/token kazancı kanıtlanmış değildir. Global skill kurulumu,
  otomatik native event ingestion ve eşzamanlı yazan worker'lar bekler.

EROL erken geliştirme aşamasındadır. [Implementation plan](docs/implementation-plan.md),
[architecture](docs/architecture.md), [capabilities](docs/capabilities.md),
[delivery report](docs/delivery-report.md).

## Lisans ve katkı

[AGPL-3.0-only](LICENSE). Gerekli bildirimleri koruyarak kullanabilir, değiştirebilir,
dağıtabilirsin; lisansın kaynak paylaşımı hükümleri geçerlidir.
[Katkı](CONTRIBUTING.md), [güvenlik bildirimi](SECURITY.md),
[issue aç](https://github.com/erolemir/EROL/issues).
