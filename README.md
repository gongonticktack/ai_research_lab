🌐 **Webアプリ：[AI Research Labを開く](https://gongonticktack.github.io/ai_research_lab/)**

# AI Research Lab

## 概要

SAM 3D Bodyの実験結果を共通JSONで記録し、検証・集計・3D表示・性能変化の検出まで行う研究用ツールです。ローカルGPUで計測した結果をGitHubへ登録すると、GitHub Actionsが集計し、GitHub Pagesのダッシュボードに反映します。

[ダッシュボードを開く](https://gongonticktack.github.io/ai_research_lab/)

## 主な機能

- JSON Schemaによる実験設定・結果の検証。
- 推論時間の中央値・95パーセンタイルと、正解データがある場合の関節位置誤差の集計。
- Three.jsによる人体メッシュ表示。
- 比較条件が一致する実測結果について、推論時間の中央値が20%を超えて増加した場合にIssueを作成。
- サンプル、実測、失敗、実行条件不足を区別して表示。

## 推奨要件

| 用途 | 環境 |
| --- | --- |
| 集計・テスト | Python 3.11、Git |
| ダッシュボード閲覧 | WebGL対応の現行ブラウザ |
| SAM 3D Body実測 | LinuxまたはWSL2、NVIDIA CUDA対応GPU・ドライバー、Python 3.11 |
| 自動公開 | GitHub ActionsとGitHub Pagesを利用できるリポジトリ |

GPUの必要メモリは入力とモデル環境に依存します。本リポジトリでは最低VRAMを定義していません。公式モデルの利用条件と重みへのアクセス権を別途確認してください。

## 必要なライブラリ

- 集計・検証：`requirements.txt`のjsonschema 4.23.0。
- 実測：CUDA対応PyTorch、torchvision、SAM 3D Bodyとその依存関係。`scripts/setup-sam3d.sh`が導入します。
- 表示：Three.js。Pythonの依存関係とは別にブラウザで使用します。

## 使い方

### 集計と閲覧

リポジトリを取得し、ルートで実行します。

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windowsでは .venv\Scripts\activate を使用
python -m pip install -r requirements.txt
python -m lab.aggregate
python -m http.server 8000 --directory docs
```

ブラウザで `http://localhost:8000/` を開きます。

### GPUで実測

1. Linux / WSL2で `bash scripts/setup-sam3d.sh` を実行します。
2. [SAM 3D Body公式リポジトリ](https://github.com/facebookresearch/sam-3d-body)の手順でモデル重みとMHRデータを取得します。セットアップスクリプトは重みを自動取得しません。
3. `experiments/sam3d.local.json` の `upstream`、`checkpoint`、`mhr`、`images` を実際のパスへ変更します。
4. `bash scripts/run-sam3d.sh` を実行します。Windowsからは `run-benchmark.bat` も利用できます。
5. `local-results/` の結果JSONとメッシュを確認します。公開する結果JSONを `results/`、対応メッシュを `docs/meshes/` に配置し、コミットします。

正解関節データを指定しない場合、関節位置誤差は未評価です。実測はCUDA必須で、CPUへ自動切替しません。

### 自動公開・Issue

GitHubのSettings → Pagesで公開元をGitHub Actionsにします。`daily.yml`はmainへのpush、手動実行、毎日07:00 JSTの予約実行に対応しています。予約時刻から開始が遅れる場合があります。

Issue候補だけ確認する場合は `python -m lab.issues` を使用します。実際に登録する `--publish` には `GITHUB_TOKEN` と `GITHUB_REPOSITORY` が必要です。Actions内ではワークフローが設定します。

## フォルダ構成

| 相対パス | 役割 |
| --- | --- |
| `lab/` | 計測、検証、集計、Issue作成 |
| `experiments/` | 入力画像・モデル・計測条件の設定 |
| `schemas/` | 実験設定と結果のJSON Schema |
| `results/` | 公開用の実験結果 |
| `docs/` | ダッシュボードと公開データ・メッシュ |
| `scripts/` | GPU環境準備、WSL実行、サンプル取得 |
| `tests/` | 集計・検証のテスト |
| `.github/workflows/` | CIと定期公開 |
| `requirements.txt` | 集計用Python依存関係 |
| `local-results/` | ローカル計測で生成される結果 |

## 仕組み

設定JSONで入力とモデルを指定し、画像ごとにウォームアップ後の推論時間を測ります。結果JSONを検証してから集計し、Web画面で表示します。同じモデル・入力・GPU・ソフトウェア条件の実測だけを比較し、サンプル結果から性能低下Issueを作成することはありません。

## 確認方法

```bash
python -m unittest discover -s tests -v
```

## トラブル対処

- `blocked`：重み、画像、依存ライブラリ、CUDAの有無と結果JSONの`notes`を確認してください。
- メッシュが表示されない：JSONのartifactパスと`docs/meshes/`の配置を確認してください。
- 公開されない：Actionsの失敗ステップとPages設定を確認してください。
