# 🎬 Video Translator AI

[英語](../../README.md) | [全翻訳](README.md)

**このページを読む場所:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

AI を活用したビデオ音声吹き替えツール。ビデオを 26 言語に自動的に文字起こし、翻訳、再吹き替えします。ローカル処理オプションがあり、デフォルトで API キーは必要ありません。 Whisper 音声認識はローカルで実行されます。 Edge-TTS、Google Translate、DeepL にはインターネット接続が必要です。オプション機能 (DeepL、話している人の識別 (日記化)) には、API キーまたはアクセス トークンが必要な場合があります。

> **v2.0** - モジュラー パッケージ、ローカル Ollama 翻訳、品質プロファイル オーケストレーション、インストール可能な Python メタデータ、実際のモデルとのオプトイン統合テスト。変更の完全なリストについては、[GitHub Releases](https://github.com/HeartB1t/VideoTranslatorAI/releases) とコミット履歴を参照してください。

## 仕組み

1. **文字起こし** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) 音声を文字起こしします (GPU アクセラレーション)
2. **音声/音楽の分離** - [Demucs](https://github.com/facebookresearch/demucs) はバックグラウンド ミュージックからボーカルを分離します
3. **翻訳** - MarianMT (ローカル、オフライン)、Google Translate、DeepL Free、または **Ollama LLM** (Qwen3、スロット対応の簡潔な翻訳)
4. **話している人の識別 (日記化)** *(オプション)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) は各セグメントで誰が話しているのかを識別します
5. **音声ダビング** - [Edge-TTS](https://github.com/rany2/edge-tts) (400 個以上の音声) または [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (音声クローン、会話内の各話者用)
6. **ミキシング** - 吹き替え音声を元の BGM とミックスバックします。
7. **正規化** - 最終オーディオは -23 LUFS (EBU R128 ブロードキャスト標準) に正規化されます。
8. **リップシンク** *(オプション)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) は口の動きを吹き替えたオーディオと同期させます。

## 特長

- 🖥️ テーマ別 GUI (Tkinter) - コマンドラインは必要ありません。 Graphite、Slate、Light、および Neon のテーマ、アクセント カラー、テキスト サイズ、設定パネルはドラッグして並べ替えることができます
- 🌍 **26 のターゲット言語**、言語ごとに複数の音声あり
- 🌐 **26 言語の UI** - インターフェース自体があなたの言語に適応します
- 🎬 **YouTube と URL のサポート** - YouTube リンクを貼り付けて直接翻訳します (yt-dlp を利用)
- ▶️ **統合ビデオプレーヤー** (libmpv/mpv) - 色分けされたトランスポートコントロール、プレイリスト、A/B オリジナルオーディオと吹き替えオーディオ、字幕の切り替え、スナップショット、全画面表示、フォルダーを開く
- ⏱️ **リアルタイム翻訳** - 翻訳された字幕と YouTube スタイルの遅延スライダーを備えたローカル ファイルまたは解決されたオンデマンド ビデオ リンクを視聴します。エンジン MarianMT / Google / DeepL / Ollama。実験的な音声ダビングでは、Edge-TTS と 2 番目の mpv インスタンスを使用します。音声オーバーラップの処理とリアル オーディオ/Windows の受け入れは引き続き進行中です。成長を続けるライブ ブロードキャストはまだサポートされていません。 [ライブ実装ステータス](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26) を参照してください。
- 🎵 Demucs による音声と音楽の分離 (BGM を維持)
- 🔇 **元の音声をミュート** は、ライブ翻訳前およびライブ翻訳中に利用可能で、翻訳された音声は聞こえるままに、ビデオのサウンドトラックを無音にします。オフに切り替えると、元のオーディオが復元されます。ライブセッションが終了するとリセットされます。
- 🧠 **MarianMT** - 完全ローカル、オフラインのニューラル翻訳 (ヘルシンキ-NLP、リクエストレート制限なし、API キーなし)
- 🤖 **Ollama LLM 翻訳** *(v2.0 の新機能)* - ローカル LLM (Qwen3、Llama、Mistral) は、自然音声吹き替え用のスロット対応の簡潔な翻訳を生成し、最初の使用時にモデルを自動検出/インストール/起動/プルします
- 🎙️ **音声クローン** - Coqui XTTS v2 は、セグメントごとの適応速度と幻覚に対するマルチシード再試行を使用して、ターゲット言語の元の音声の声で話している人のクローンを作成します (~1.8 GB モデル)。
- 👥 **話している人の識別 (日記化)** - pyannote-audio 3.1 は話している複数の人を識別します。 XTTS は各音声を個別にクローンします。
- 💋 **リップシンク** - Wav2Lip GAN は口の動きを吹き替えられたオーディオと同期させます (~416 MB モデル)
- 🔊 **オーディオ正規化** - 自動 -23 LUFS ラウドネス正規化 (EBU R128)
- ✏️ 字幕エディタ - 音声吹き替え前に字幕を確認して修正します
- 📦 バッチ処理 - 複数の動画または URL を一度に翻訳します
- ⚡ CUDA による GPU アクセラレーション (自動的に CPU にフォールバック)
- 📄 オプションの`.srt`字幕エクスポート
- 🔁 **DeepL Free** 翻訳エンジン (オプション - 500,000 文字/月、無料の API キーが必要)
- 🔧 **自動インストール** - 不足している Python パッケージと ffmpeg は初回起動時に自動的にインストールされます

## サポートされている言語

アラビア語、中国語、チェコ語、デンマーク語、オランダ語、英語、フィンランド語、フランス語、ドイツ語、ギリシャ語、ヒンディー語、ハンガリー語、インドネシア語、イタリア語、日本語、韓国語、ノルウェー語、ポーランド語、ポルトガル語、ルーマニア語、ロシア語、スペイン語、スウェーデン語、トルコ語、ウクライナ語、ベトナム語

## 音声カタログ

Edge-TTS 音声カタログは、`video_translator_gui.py` の先頭近くの `LANGUAGES` で定義されます。この辞書は、ターゲット言語名、GUI 音声ラジオ ボタン、および `--voice` が省略された場合の CLI フォールバック音声の信頼できる情報源です。

クロード/プロジェクト メンテナンス ノートには、**Voice Catalog Source Of Truth** の下の `CLAUDE.md` のこの場所が反映されているため、将来のコード エージェントは、音声を更新する場所と README がユーザーに指示する場所を知ることができます。

## 翻訳エンジン

| エンジン | セットアップ | 限界 | 品質 |
|--------|-------|--------|---------|
| **Google Translate** *(デフォルト)* | なし | 非公式のスクレイピング - 大きなビデオでは制限される可能性があります | ★★★★ |
| **MarianMT** | なし - 初回使用時に言語ペアごとに最大 298 MB をダウンロードします | なし - ダウンロード後は完全にオフライン | ★★★★ |
| **DeepL Free** | [deepl.com](https://www.deepl.com/pro-api) の無料 API キー | 500,000 文字/月 | ★★★★★ |
| **Ollama LLM** *(音声吹き替えに推奨 - v2.0 の新機能)* | 初回使用時に自動インストール (~1 GB Ollama + 5 GB モデル) | なし - 完全にローカル | ★★★★★ |

> **MarianMT** は、最初のダウンロード後にローカルにキャッシュされた [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) モデルを使用します。明示的なソース言語が必要です (自動検出はサポートされていません - ソース言語を手動で選択します)。必要な Python パッケージ (`sacremoses`、`sentencepiece`) が存在しない場合は、最初の選択で自動的にインストールされます。

> **Ollama LLM** *(v2.0 の新機能)* は、ターゲットのタイムスロットを意識した翻訳を生成するため、音声吹き替えに推奨されるエンジンです。 MarianMT が文字通りに翻訳し、英語よりも最大 25% 長いイタリア語/スペイン語/フランス語を生成する (TTS で可聴音声圧縮を強制する) 場合、LLM は各セグメントを簡潔で自然な音声配信に保つように求められ、ソースに対して 0.85 ～ 0.95 の一般的な文字比を達成します。デフォルトのモデルは `qwen3:8b` (ディスク上 5.2 GB、最大 6 GB VRAM) です。 `qwen3:4b` (~3 GB) は軽量のオプションで、`qwen3:14b` は高品質のオプションです。パイプラインは Ollama バイナリを自動検出し、初回使用時に公式インストーラー経由で自動インストールし (同意ポップアップあり)、デーモンを起動して選択したモデルをプルします。手動セットアップは必要ありません。不足しているものがあれば、自動的に Google Translate に切り替わります。

## 音声クローン作成 (XTTS v2)

有効にすると、アプリは元のビデオから話者の音声を抽出し、それを参照として使用してターゲット言語の音声を複製します。

- サポート言語: AR、ZH、CS、DE、EN、ES、FR、HI、HU、IT、JA、KO、NL、PL、PT、RU、TR (17/26)
- 残りの 9 言語については、Edge-TTS がフォールバックとして自動的に使用されます。
- モデル (~1.8 GB) は初回使用時に `~/.local/share/tts/` に自動的にダウンロードされます
- **VAD フィルタリングされたリファレンス** (v1.4): 音声クローンの品質を向上させるために、[silero-vad](https://github.com/snakers4/silero-vad) を介して元の音声から選択された 10 ～ 15 秒の連続音声
- **生成速度** 構成可能 (`xtts_speed`、デフォルト `1.25`): 値を大きくすると、翻訳されたテキストがソース スロットより長い場合、後処理オーディオ圧縮アーティファクトが軽減されます。 `~/.config/videotranslatorai/config.json` または CLI `--xtts-speed` 経由で調整する
- CUDA または CPU 上で実行

## 話している人の識別 (日記化) (pyannote-audio)

有効にすると、アプリは各セグメントで誰が話しているのかを識別します。 Voice Cloning と組み合わせると、各話者の音声が個別にクローン化されるため、インタビュー、ポッドキャスト、複数人のビデオに最適です。

- 無料の [HuggingFace トークン](https://huggingface.co/settings/tokens) が必要です (1 回限りの登録)
- **OS キーリング経由で安全に保存されたトークン** (v1.4): Windows Credential Manager、macOS Keychain、Linux Secret Service。以前の平文 JSON ストレージからの自動移行
- 最初のダウンロード後は完全にオフラインで動作します
- モデル: `pyannote/speaker-diarization-3.1`

## リップシンク（Wav2Lip）

有効にすると、アプリは Wav2Lip GAN を適用して対象者の口の動きを吹き替え音声と同期させます。その人は翻訳された言語を話しているように見えます。

- モデル (~416 MB) とリポジトリは、初回使用時に自動的に `~/.local/share/wav2lip/` に複製されます。
- CUDA (推奨) または CPU で実行
- 処理時間が大幅に増加する
- 顔が 1 つだけはっきりと見えるビデオで最も効果的です

## 要件

- Python 3.10+ (Windows インストーラーは 3.11.9 を自動的にプロビジョニングします)
- Windows 10 / 11 (x64)、Linux、または macOS
- **NVIDIA GPU を強く推奨** - 以下の GPU 表を参照してください。
- フル インストールの場合は 20 GB の空きディスク容量 (PyTorch CUDA、Whisperlarge-v3、XTTS、Wav2Lip)

> **ffmpeg とすべての Python パッケージが存在しない場合は、最初の起動時に自動的にインストールされます**。手動セットアップは必要ありません。

**オプションのシステム依存関係** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`、macOS: `brew install rubberband`)。インストールすると、プロファイルで制御された品質帯域 (デフォルトは 1.15 ～ 1.50、ハード コンテンツの場合は最大 1.65) でピッチを保持するタイムストレッチに使用され、クローンされた XTTS 音声に残っている「シマリス」効果が除去されます。パイプラインはそれなしで変更されずに実行されます (ffmpeg `atempo` への自動フォールバック)。品質プロファイルでは、オーディオの極端な高速化よりも、追加の短い翻訳の再試行が優先されるようになりました。

### GPUのサポート

このパイプラインは 5 つの GPU アクセラレーション コンポーネント (faster-whisper、Demucs、XTTS、Wav2Lip、pyannote) を使用します。 GPU の適用範囲はベンダー間で均一ではありません。

| GPU | Windows | Linux | 注意事項 |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx 以降、CUDA 12.4 ドライバー) | ✅フル加速 | ✅フル加速 | **推奨。** 5 つのコンポーネントはすべて GPU 上で実行されます。 |
| **AMD** (Radeon) | ⚠️ 不完全 (DirectML は XTTS および faster-whisper をサポートしていません) | ⚠️ 部分的 (ROCm は Demucs/XTTS/pyannote で動作しますが、faster-whisper は CUDA のみをサポートします) | 動作しますが、Whisper 転写が CPU 上に留まり、合計時間を支配します。 |
| **Intel Arc** | ⚠️ 未熟な PyTorch XPU サポート | ⚠️同じです | テストされていません。 |
| **なし (CPU のみ)** | ✅ 作品 | ✅ 作品 | リアルタイムより **10 ～ 20 倍遅い**ことが予想されます。 5 分のクリップを Whisperlarge-v3 で転写するだけで 50 分以上かかる場合があります。 |

**推奨される NVIDIA VRAM:**

| VRAM | 代表的なグラフィックカード | 経験 |
|------|---------------|-----------|
| 6GB | GTX 1660、RTX 2060 | 使用可能ですが、XTTS + Wav2Lip を同時に実行することはできません |
| 8GB | RTX 3060 Ti、4060 | フルパイプライン、マージンなし |
| **12 GB+** | **RTX 3060 12GB、4070、4080** | **推奨 - 快適** |
| 24GB | RTX 3090、4090 | 大規模なバッチに対応する予備容量 |

## インストール

### Windows

1. このリポジトリのクローンを作成またはダウンロードします
2. `setup_windows.bat` を右クリック → **管理者として実行** → メニューに `[1] Install` が表示されます
3. インストーラーは自動的に次のことを行います。
   - Python 3.11 が存在しない場合はインストールします (システム全体)
   - 存在しない場合は、Git for Windows をインストールします
   - すべての Python 依存関係 (PyTorch CUDA 12.4、faster-whisper、Demucs、coqui-tts、Wav2Lip deps など) をインストールします。
   - ffmpegをダウンロードしてインストールします
   - 統合ビデオプレーヤー (Python-mpv と `mpv-runtime` の libmpv ビルド) をインストールします。このステップはオプションです。失敗した場合、他のすべてが機能し、プレーヤー ペインに何が足りないのかが説明されます。
   - **パブリック デスクトップ ショートカット**を作成します (PC 上のすべての Windows アカウントに表示されます)

> インストーラーは **マルチユーザー** です。すべてが `%ProgramFiles%\VideoTranslatorAI` の下にシステム全体にインストールされ、マシン上の Windows ユーザーであればすぐに使用できるショートカットを見つけることができます。 VS C++ ビルド ツールは **不要になりました** - 維持されている `coqui-tts` フォークは、プリコンパイルされた Python ホイール パッケージを提供します。

### Linux / macOS

```bash
# リポジトリのクローンを作成する
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# オプション: テスト済みの NVIDIA CUDA 12.4 PyTorch スタックを前面にインストールします
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# オプション: GUI を使用せずに、すべての Python ランタイム パッケージをプレインストールします。
# 不足しているパッケージを最初の実行時にインストールする
pip install --break-system-packages -r requirements.txt

# オプション: 統合ビデオプレーヤー (ディストリビューションからの libmpv、PyPI からの python-mpv)
sudo apt install libmpv2        # Fedora: mpv-libs、Arch: mpv、openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# オプション: プロジェクトを編集可能な Python パッケージとしてインストールします
pip install --break-system-packages --no-deps -e .

# ソースから起動
python video_translator_gui.py

# または、編集可能/パッケージのインストール後
videotranslatorai
videotranslatorai --preflight
```

> 最初の起動時に、GUI は不足しているパッケージ (faster-whisper、Demucs、Edge-TTS など) を検出し、それらを自動的にインストールし、出力をログ ウィンドウにストリーミングします。 ffmpeg は、`apt-get` / `dnf` / `pacman` (Linux) 経由で自動的にインストールされるか、GitHub (Windows) からダウンロードされます。

> ヘッダーには **プレイヤー** バッジが表示されます。 libmpv または python-mpv が見つからない場合、左側のペインに何が足りないのかが表示され、**プレイヤーのインストール** が表示されます。Linux では、pkexec (その後は `sudo -n`) を介してパッケージ マネージャーが使用され、どちらも機能しない場合は手動コマンドが表示されます。 Windows では、現在のユーザーの libmpv (約 32 MB) をダウンロードする前に質問されます。

### 要件プロファイル

| ファイル | 目的 |
|------|---------|
| `requirements.txt` | 完全な下位互換性のあるランタイムのインストール。 |
| `requirements-core.txt` | GUI/CLI で使用されるデフォルトのパイプライン パッケージ。 |
| `requirements-optional.txt` | XTTS、MarianMT トークナイザー、日記化、VAD、キーリング。 |
| `requirements-wav2lip.txt` | Wav2Lip ランタイムおよび顔検出スタック (`new-basicsr`、`facexlib`、`dlib`)。 |
| `requirements-gpu-cu124.txt` | PyTorch スタックは NVIDIA CUDA 12.4 ホイールでテストされました。 |
| `requirements-player.txt` | 統合ビデオプレーヤー: python-mpv (システムまたは Windows インストーラーからの libmpv が必要)。 |
| `requirements-dev.txt` | CI/単体テストで使用される軽量の依存関係。 |

## アンインストール

### Windows

`setup_windows.bat` を実行し (右クリック → **管理者として実行**)、メニューから `[3] Uninstall` を選択します。 3 つのアンインストール サブモードが提供されています。

| モード | 管理者が必要です | 範囲 |
|------|----------------|-------|
| **[1] 完全なアンインストール - ワンクリック** | ✅ | アプリ フォルダー、パブリック デスクトップ ショートカット、マシン PATH からの ffmpeg、すべてのユーザーの HF モデル キャッシュ (Whisper/XTTS) と構成 (`HF token`)、およびインストーラーによってインストールされたすべての Python AI パッケージを削除します。最後に、レジストリの Quiet-uninstall 文字列を介して **Python 3.11** と **Git for Windows** をサイレント アンインストールするかどうかも尋ねられます (オプトイン)。 |
| **[2] 現在のユーザーのみ** | ❌ | 実行中のユーザーの VTAI 構成、HF/XTTS キャッシュ、および従来のユーザーごとのインストールのみを削除します。 **システム全体のインストールはそのまま残る**ため、PC 上の他の Windows アカウントはアプリを使い続けることができます。 |
| **[3] カスタム - 詳細** | ✅ システム項目の場合、 ❌ ユーザー項目の場合 | カテゴリごとに Y/N プロンプト: アプリ フォルダー、ショートカット、マシン PATH、ユーザーごとのレガシー インストール、ユーザーごとの構成/キャッシュ、次にグループ化された Python パッケージ (TTS、PyTorch スタック、Whisper+ctranslate2、Demucs、Wav2Lip deps、pyannote、パイプライン ユーティリティ)、最後にオプションの Python 3.11 と Git。 |

**自動的に削除されることはありません:** Visual Studio C++ ビルド ツール (古い実行で存在する場合)。必要に応じて、Windows 設定の *アプリと機能* を使用して手動で削除します。

### Linux / macOS

専用のアンインストーラーはありません - 手動で削除します。

```bash
# GUI の自動インストーラーによってインストールされた Python パッケージ
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# ユーザーデータとモデルのキャッシュ
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (テーマ、パネルの順序、設定)
rm -f  ~/.videotranslatorai_config.json     # バージョン 1.9 以下のレガシー構成 (存在する場合)
```

## 使用法

### 診断

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

翻訳を開始したり、何もインストールしたりせずに、ローカル環境診断を実行します。 `--preflight-lipsync` は Wav2Lip フェイス パッケージを必要に応じて処理します。これは **リップ シンク**を有効にする前に役立ちます。 GUI は、ログ パネルの [**診断**] ボタンから同じ基本チェックを公開します。 `--preflight-player` は、必要に応じて統合ビデオ プレーヤー (python-mpv およびロード可能な libmpv) を処理します。 `python -m videotranslator.libmpv_runtime check` は libmpv のみをプローブします (出口 0 は準備完了、2 は利用不可)。

### GUI

```bash
python video_translator_gui.py
```

**レイアウト:** バッチ翻訳設定は、設定パネルのスタックとして右側の列に表示されます: **入力**、**翻訳**、**ワークフロー プロファイル**、**開始**、および折りたたみ可能な詳細セクション (モデル、翻訳エンジン、オーディオ、音声クローン、リップ シンク、ダイアライゼーション、オプション、ホットワード)。左側の大きな領域は **統合ビデオ プレーヤー** (トランスポート、プレイリスト、A/B オリジナル音声と吹き替え音声、字幕、スナップショット、フルスクリーン) で、その下に **リアルタイム翻訳** バーがあります。カードをタイトルまたは **≡** ハンドルでドラッグして、列の上または下に移動します。注文は保存され (`ui_panel_order`)、次回の開始時に復元されます。下部のログ パネルは、**ログを非表示** で非表示にできます。起動すると、ウィンドウは現在のモニター (ポインターの下にあるモニター) を中心に最大化されて開きます。そのため、マルチモニター設定でも適切に動作します。

**ビデオ ビデオ プレーヤー コントロール:** アイコンは、選択したアクセント カラーに関係なく、すべてのテーマで一貫した機能色を使用します。

| 制御 | 色 |
|---------|--------|
| ビデオを再生する | 緑 |
| 一時停止 (再生中の再生の代わり) | アンバー |
| 再生を停止する | コーラルレッド |
| 前へ / 10 秒戻る / 10 秒進む / 次へ | ブルー |
| スナップショット | バイオレット |
| フォルダーを開く | ゴールド |

ホバリングすると、微妙な色合いの背景が追加されます。使用できないコントロールは中立です。プレイリスト ナビゲーションは停止後も引き続き使用できます。ツールチップとキーボード フォーカス インジケーターは引き続き利用できるため、アクションを識別する唯一の方法は色ではありません。

**ローカル ファイルから:**
1. [**追加**] をクリックして 1 つ以上のビデオ ファイルを選択します
2. ソース言語とターゲット言語を選択してください
3. **モデル** セクションを開き、Whisper モデルを選択します (`small` は速度と精度のバランスが優れています)
4. 音声を選択し、必要に応じて TTS 速度を調整します
5. *(オプション)* **翻訳エンジン** で **Google** (デフォルト)、**MarianMT** (ローカル/オフライン)、**DeepL Free**、または **Ollama LLM** (ローカル、音声吹き替えに推奨) を選択します。
6. *(オプション)* **音声クローン** (XTTS v2) および/または **話している人の識別 (ダイアライゼーション)** を有効にします
7. *(オプション)* **リップシンク** (Wav2Lip) を有効にする
8. **翻訳を開始**をクリックします

**YouTube (またはサポートされているサイト) から:**
1. **URL** フィールドに 1 つ以上の URL を貼り付けます (1 行に 1 つ)
2. 通常どおり言語、モデル、音声を設定します
3. **⬇ ダウンロードと翻訳** をクリックします

> yt-dlp は YouTube、Vimeo、Twitter/X、TikTok、および [1000 以上のその他のサイト](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) をサポートしています。

> ⚠️ **フェアユースに関する通知:** yt-dlp 経由でビデオをダウンロードすると、YouTube などのプラットフォームによる自動アクセスとみなされ、利用規約に違反する可能性があります。同じ IP アドレスから頻繁に使用したり、繰り返し使用したりすると、一時的なブロック (HTTP 429 / サインインが必要なエラー) が発生する可能性があります。ダウンロードに失敗した場合は、VPN を使用するか、IP をローテーションしてください。このツールは個人的な非営利使用のみを目的としています。翻訳されたコンテンツの再配布は著作権を侵害する可能性があります。常に元の作成者の権利を尊重してください。

### リアルタイム翻訳（字幕と実験的な音声吹き替え）

翻訳された字幕とオプションの音声翻訳を使用して、ローカル ファイルまたは解決されたオンデマンド ビデオ リンクを視聴します。プレーヤーの下のバーを使用します。

**リンクより:**

1. **URL** フィールドにリンクを貼り付けます
2. ソース言語とターゲット言語を設定し、音声を選択し、**遅延** スライダーを調整します。
3. **吹き替え音声** および/または **字幕** を選択します
4. 翻訳された音声のみを聞くには、開始する前に **元の音声をミュート** を選択します (イタリア語: **Silenzia originale**、字幕チェックボックスの横)
5. **リアルタイムで翻訳** をクリックすると、リンクが解決され、翻訳が開始されます。

**ロードされたファイルから:** プレーヤーにビデオをロードし ([入力] -> [追加] を選択してから選択します)、URL フィールドを空のままにし、同じライブ設定を選択して、**リアルタイムで翻訳** をクリックします。フィールドが空でない場合は、URL が優先されます。

- **エンジン:** MarianMT (オフライン、デフォルト)、Google、DeepL、または Ollama。音声認識 (Whisper) はローカルで実行されます。オフライン モデルには初期ダウンロードが必要です。
- **音声吹き替え:** 2 番目の mpv インスタンスを介した実験的な Edge-TTS 音声再生。これにはインターネット アクセスが必要で、バッチ音声クローン作成とは別のものです。
- **元の音声をミュート:** 翻訳開始前と翻訳中の両方で利用できます。音楽やエフェクトを含むオリジナルのサウンドトラック全体が沈黙しますが、翻訳された音声は聞こえるままになります。元の音声で話している人を分離しません。サウンドトラックを復元するには、オフに切り替えます。ライブセッションが終了するとリセットされます。プレーヤーのスピーカー ボタンは一般的なミュートであり、この独立したコントロールではありません。
- **一時停止とシーク:** ビデオ プレーヤーのコントロールはライブ セッションに接続されています。エンドツーエンドのオーディオ同期には、依然としてプラットフォーム固有の受け入れテストが必要です。
- **現在の制限:** クリップのオーバーラップ/フェードの処理、オーディオ タイミングの調整、および Windows の受け入れはオープンのままです。拡大するライブ ブロードキャストはまだサポートされていません。ライブ モード ラベルは、成長に伴うブロードキャストの取り込みのサポートを意味するものではありません。 [実装状況と残作業](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26)を参照してください。

保存された吹き替えビデオの場合は、リアルタイム プレビューの代わりに **ダウンロードと翻訳** / **翻訳の開始** を使用します。

### 翻訳エンジンブロックとVPN

修正が異なる 2 つの異なるブロックが発生する可能性があります。

| ブロック | 症状 | 修正 |
|-------|---------|-----|
| **ダウンロード** (yt-dlp) | 「サインインしてボットではないことを確認してください」、HTTP 429 | **VPN** / IP をローテーションするか、ブラウザで YouTube にログインします (Cookie は自動的に読み取られます) |
| **翻訳** (Google 無料エンドポイント) | 「Google Translate は翻訳できませんでした...リクエストレートが制限されています/ブロックされました」 | **MarianMT** (オフライン) または **Ollama** (ローカル) を使用します。リクエスト レート制限はありません。 VPN も役立ちます。 Google がブロックされた場合、バッチ フローは **自動的に MarianMT にフォールバックする**ようになりました。 |

### テーマと外観

ヘッダーの歯車アイコンをクリックして **設定** を開きます。

- **テーマ**: 自動 (OS のダーク/ライト モードに従います)、Graphite (デフォルト)、Slate、Light、Neon。
- **アクセントカラー**: テーマごとのデフォルト、またはブルー、ティール、バイオレット、グリーン、アンバー、ローズ。
- **文字サイズ**: 小、標準、大、特大。
- **インターフェース言語**: 26 言語。

変更は再起動せずにすぐに適用され、構成ファイル (`ui_theme`、`ui_accent`、`ui_scale`、`ui_lang`) に保存されます。 **デフォルトに戻す** は、Graphite テーマ、デフォルトのアクセント、通常のテキスト サイズ、設定パネルのデフォルトの順序を戻します。

### コマンドライン

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**すべてのオプション:**

| CLI オプション | 説明 | デフォルト |
|------|-------------|---------|
| `--lang-source` | ソース言語 (自動検出の場合は `auto`) | `auto` |
| `--lang-target` | ターゲット言語コード (例: `it`、`fr`、`de`) | `it` |
| `--voice` | Edge-TTS 音声名 | auto |
| `--model` | Whisperモデル（`tiny`→`large-v3-turbo`） | `small` |
| `--tts-rate` | TTS 速度調整 (例: `+10%`、`-20%`) | `+0%` |
| `--translation-engine` | `google`、`marian`、または `deepl` | `google` |
| `--deepl-key` | DeepL Free API キー | - |
| `--diarize` | 話している人の識別を有効にする (日記化) (pyannote) | - |
| `--hf-token` | 日記用のHuggingFaceトークン | - |
| `--lipsync` | 音声アフレコ後に Wav2Lip リップシンクを適用する | - |
| `--subs-only` | `.srt` のみを生成し、音声ダビングをスキップします | - |
| `--no-subs` | `.srt` 世代をスキップします | - |
| `--no-demucs` | 音声と音楽の分離をスキップする | - |
| `--output` / `-o` | 出力ファイルのパス | auto |
| `--output-dir` | 翻訳済みファイルのフォルダー (1 か所、Windows および Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | 複数のファイルを処理する | - |

### 実際のモデルとの統合テスト

デフォルトのテスト スイートでは、実際のモデルのダウンロードと長時間にわたる GPU 作業が回避されます。インストールされたローカル スタックに対してオプトインの経験的チェックを実行するには、次の手順を実行します。

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

これらのチェックでは、実際の Wav2Lip インポート、Torch CUDA の可用性、Ollama デーモンの可用性、および合成音声の faster-Whisper を検証します。ローカルのドライバー/デーモン/モデルの状態が準備できていない場合、意図的に失敗するかスキップします。

**例:**

```bash
# 地元の MarianMT でイタリア語のビデオを英語に翻訳します
# (最初の使用時に最大 298 MB のモデルをダウンロードし、その後は完全にオフラインになります)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# 音声クローン + 話している人の識別による翻訳 (日記化)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# リップシンクで翻訳する
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# 字幕のみ（吹き替えなし）
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper モデル

| モデル | サイズ | 速度 | 精度 |
|-------|------|-------|----------|
| tiny | 75MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465MB | ⚡⚡ | ★★★☆ |
| medium | 1.5GB | ⚡ | ★★★★ |
| large-v2/v3 | 3GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1.6GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` は、`large-v3` (デコーダー層が 4 層対 32 層) の蒸留バージョンで、ほぼ `medium` 層の速度でほぼ高品質です。転写速度が重要な場合、最新の GPU で推奨されるデフォルト。多言語資料の品質低下は軽微です。

> モデルは初めて使用するときに自動的にダウンロードされます。

## スタンドアロンモジュールのCLI

モジュラー パッケージは、完全なパイプラインを起動せずに直接呼び出すことができる 4 つのユーザー向けツールを公開します。

```bash
# 顔の存在についてビデオをプリフライトします (存在しない場合、Wav2Lip はスキップします)。
python3 -m videotranslator.face_detector path/to/video.mp4
# 出口 0 = 顔が存在する、出口 1 = 顔なし

# build_dubbed_track によって生成された *_metrics.csv を分析します。
# pre_stretch_ratio の P50/P75/P90/P95、可聴帯域の内訳をレポートします。
# ストレッチ エンジンの使用状況と、ターゲット テキストの最悪の外れ値のトップ N です。
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# TTS 用にテキストをサニタイズします (コロン、セミコロン、省略記号、ダッシュを書き換えます)。
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# TTS を実行する前に、.srt または .json セグメント ファイルから音声吹き替えの難易度を推定します。
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

各ツールには、完全なオプションの `-h`/`--help` があります。これらは自己完結型であり、音声吹き替えパイプラインが依存する同じモジュールを再利用するため、出力はランタイムと一貫性を保ちます。

## ライセンス

MIT

### サードパーティ製コンポーネント

リポジトリコードはMITです。インストーラーは、インストール時に独自のソースから以下のコンポーネントをダウンロードします。プロジェクトはそれらを再配布しません。

- **libmpv** (https://github.com/mpv-player/mpv)、統合ビデオ プレーヤーのエンジン。 Windows: zhongfly による LGPL ビルド (https://github.com/zhongfly/mpv-winbuild) が最初に試行されます。 shinchiro によるピン留めされた GPL ビルド (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) がフォールバックです。 `mpv-runtime\BUILD.txt` はソース、ライセンス フレーバー、mpv コミットを記録し、ライセンス テキストは DLL の隣にあります。 Linux: 配布パッケージ (`libmpv2`、`libmpv1`、`mpv-libs` または `mpv`)。
- libmpv 内の **FFmpeg** (libmpv ビルド後の LGPL または GPL)。
- **python-mpv** (PyPI 上の `mpv`)、GPLv2+ または LGPLv2.1+。
- **7-Zip `7zr.exe`** 26.03 (LGPL)。libmpv を抽出するために Windows インストーラーによって使用され、その後削除されます。
- **Vulkan ローダー** (Khronos、MIT および Apache-2.0)。`vulkan-1.dll` が見つからない場合にのみ Windows にダウンロードされます。
- **edge-tts** (LGPLv3)、音声吹き替えパイプラインによって使用されます。
- **MarianMT モデル** (ヘルシンキ-NLP)、Hugging Face Hub からダウンロードされたものは、最初は独自のライセンスに基づいて使用されます (`opus-mt` モデルの場合は Apache-2.0、`opus-mt-tc-big` の場合は CC-BY-4.0)。
