# AI Research Lab

3D・AI研究の自動実験ラボ。共通JSON → 検証 → 集計 → Three.js表示 → 実測の性能変化をIssue化する最小構成です。

**現状はサンプル1件、SAM実測0件です。サンプルの数値は架空で、モデル性能を示しません。**

## 構成・データの流れ

|機能|実装|動作|
|---|---|---|
|共通仕様|`schemas/*.schema.json` / Python jsonschema|結果と実験設定を検証、不明な項目や非有限値を拒否|
|SAM推論|`lab/benchmark.py` / Meta SAM 3D Body / PyTorch|手元CUDAで単一人物画像を推論、モデル・入力のSHA256と上流コミットを記録|
|ベンチマーク|`lab/metrics.py`|入力ごとに1回ウォームアップ、繰り返しのp50/p95、同一MHR70順序の正解があれば骨盤相対MPJPE|
|分析|`lab/aggregate.py`|サンプルを性能比較から除外、同条件の直近実測ペアを比較|
|表示|`docs/` / HTML CSS JavaScript / Three.js 0.170.0|絞り込み、JSON閲覧、3Dメッシュ回転、読み込みエラー表示|
|日次処理|`.github/workflows/daily.yml`|毎朝7時JST（22時UTC）、集計・Issue化・Pages公開。遅延する場合あり|
|Issue連携|`lab/issues.py` / GitHub API|p50が20%超悪化した実測を1実験1Issueで通知。閉じたIssueを再作成しない|

入力画像・モデルは `private-data/` と `checkpoints/`、推論出力は `local-results/` に置き、Git対象から除外します。公開の `results/` に移す前に、JSONのパスやnotes、人物メッシュに公開してよい内容だけが含まれていることを確認してください。GitHub Pagesは公開です。画像やチェックポイントを自動アップロードする処理はありません。

Three.jsだけはjsDelivrから取得します。利用者のブラウザーから同CDNに接続します。CDN/WebGLが使えなくても表と集計は表示できます。

## 無料を優先する構成

公開リポジトリの標準GitHub-hosted runnerで軽量な集計のみ実行します。有料GPU runner、外部AI API、クラウドGPUの契約・起動は行いません。SAM推論は手元のGPUか、利用者が確保した実行環境で行います。無料Colab/KaggleのGPUは割当保証がなく、このリポジトリでは確保や動作確認をしていません。課金条件は[GitHub公式](https://docs.github.com/en/billing/concepts/product-billing/github-actions)を参照してください。

## 最初の確認（GPU不要）

Python 3.11以降を使い、リポジトリのルートで:

```bash
python -m venv .venv
# Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m lab.aggregate
python -m lab.issues          # 投稿せず候補を表示
python -m http.server 8000 --directory docs
```

ブラウザーで `http://localhost:8000` を開きます。停止はターミナルでCtrl+C。表示が更新されない場合は再集計とブラウザー更新をしてください。初期表示の3Dは合成四面体で、人体の推定メッシュではありません。

## SAM 3D Bodyの実行

公式コードは推論時にCUDAを指定しており、CPU実測は提供しません。Linux/WSL2 + NVIDIA CUDA環境、Python 3.11、モデルの利用許可と単一人物画像が必要です。

1. [公式INSTALL](https://github.com/facebookresearch/sam-3d-body/blob/main/INSTALL.md)とモデルライセンスを確認し、[Hugging Faceモデル](https://huggingface.co/facebook/sam-3d-body-dinov3)にアクセス申請。
2. Linux/WSL2で `bash scripts/setup-sam3d.sh` を実行。PyTorch CUDA 12.8を使う初期構成です。上流・ライブラリの組合せはGPU上で未検証なので、依存エラーは公式手順と照合してください。
3. `source .venv-sam/bin/activate` の後、`hf auth login` を自分で実行し、`hf download facebook/sam-3d-body-dinov3 --local-dir checkpoints/sam-3d-body-dinov3` でモデルとMHR資産・model_config.yamlを取得。
4. `python scripts/download-example.py` で公開サンプル画像を取得、または `private-data/image-001.jpg` に単一人物の使用許可がある画像を置く。設定は `experiments/sam3d.local.json`。複数人物の検出器・FOVモデルは使わず全画像を1人物として処理します。
5. `python -m lab.benchmark --config experiments/sam3d.local.json` を実行。

このPCではUbuntu-22.04の既存 `sam3d-blackwell` 環境（Python 3.11 / PyTorch 2.8.0+cu128）を確認し、RTX 5070 TiのCUDA計算と公式SAM APIのimportが通りました。ローカルの `vendor/sam-3d-body` に公式コードを取得済みです（コミット `b5c765a0d89d789985e186d396315e7590887b94`）。公開サンプル画像は取得済み、チェックポイントとMHRモデルは未取得です。環境のimport成功はモデル推論の成功を意味しません。

このPCでは `run-benchmark.bat` を開くと既存WSL環境で実行できます。別のPCではLinux環境とモデルの準備が必要です。WSL環境名が異なる場合は `scripts/run-sam3d-wsl.ps1` を修正してください。ダウンロード版に上流コードは含まれないため `scripts/setup-sam3d.sh` で取得します。

不足条件は `blocked`、処理エラーは `failed`、集計指標はnullで保存して終了コード2を返します。モデル読み込みとメッシュ保存は時間計測から除外し、画像デコードを含む推論全体をCUDA同期して計測します。プロトコルが異なる公表値との直接比較はしないでください。

MPJPEを計算するなら画像設定の `ground_truth` にJSONパスを指定します。形式は `{"joint_layout":"mhr70","units":"meters","joints":[[x,y,z], ...]}` で70関節が必要です。左右の股関節（インデックス9・10）の中点を骨盤として相対座標に変換し、Procrustes整列はしません。正解がなければMPJPEはnullです。

### 公開サンプルの出典

[Free use human standing simple 2](https://commons.wikimedia.org/wiki/File:Free_use_human_standing_simple_2.jpg), Irawanthea92, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)。原本JPEGを変更せず取得しました。出典と公開元SHA-1は `experiments/example-source.json`、取得処理は `scripts/download-example.py` に保存しています。画像のSHA256は `81f44a9169d011de8cbd53e749ff4f48ef04fd8d2b3da6d6946c8075ce62282c` です。画像はGit対象外です。この1枚は推論の動作確認用で、3D正解はなく、精度ベンチマークの代表データではありません。

## 結果の公開・Pages

確認した結果JSONを `results/` にコミットすると集計が更新されます。メッシュの公開が必要な場合だけ `export_mesh:true` とし、出力の `meshes/` を `docs/meshes/` にコピーします。JSON内のartifactsはその相対パスです。

Settings → Pages → Build and deployment → Sourceを **GitHub Actions** にします。Actionsの「Daily aggregation and Pages」を手動実行できます。日次ジョブはGPU推論を実行せず、登録済み結果を再集計します。mainへのpushでCIとPages公開が走ります。PRでは読取専用の検証だけを行います。

## Google Drive連携

既存のGoogle Driveコネクタで入力や結果のファイルを検索・取得し、ローカルの `private-data/` に置く運用です。今回の検索では `ai-research-lab` / `SAM` に一致するデータは見つかりませんでした。指定フォルダーがないためアーカイブ先は未設定です。コネクタの認証をGitHub Actionsへ流用することはできません。無人同期が必要なら別途OAuth/サービスアカウントと非公開フォルダーを設定する必要があります（自動同期は未実装）。

## 検証範囲と未完了

JSON検証、集計、サンプル除外、MPJPEの単位/平行移動、不足入力の扱い、Issue重複防止の15テストがローカルとGitHub Actionsで成功しました。日次集計とPages公開も成功し、公開ページのフィルターと3D合成メッシュ表示を確認しました。GPU推論・モデルダウンロード・実画像精度評価はモデルがないため未実行です。比較は記述的な変化検出で統計的な有意差ではありません。

上流: [Meta SAM 3D Body](https://github.com/facebookresearch/sam-3d-body)。上流コードやチェックポイントは配布に含めません。実験環境の全依存関係は完全固定ではなく、実測結果には上流コミットを記録します。
