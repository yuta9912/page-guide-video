---
name: page-guide-video
description: Webページ・Webサービスの「使い方動画」を、撮影も編集ソフトも使わずに作る。ブラウザを自動で操作して録画し、カーソル・クリックの丸・注目の枠・下の字幕を付けた mp4 にする。「このページの使い方動画を作って」「操作説明の動画」「サイトの案内動画」「画面録画で解説して」と言われたら使う。
---

# page-guide-video — Webページの使い方動画

作業ディレクトリ: このスキルのフォルダ（`scripts/record_guide.py` がある場所）。
DesignNOW の MCP（designnow_skill）で読んでいる場合は、`scripts/record_guide.py` と `guides/sample.json` を path 指定で受け取り、利用者のパソコンの作業フォルダ（例：`~/使い方動画/`）に同じ並びで書き出してから動かす。

## できあがるもの

- ページを自動で操作している画面の録画（1920px 幅・30fps の mp4）
- 黒いカーソルが動き、押す所に**青い丸**、見てほしい所に**オレンジの枠**が出る
- 画面の下に**字幕**（声は入らない）

## 準備（AIが自動でやる。利用者に「入れてください」と頼まない）

録画の道具は、**作業フォルダの中だけ**に自動で用意する。Mac のアプリや設定には触らないので、利用者に許可を求めたり、インストールをお願いしたりしない。2回目からはこの手順はいらない（`.venv` があれば飛ばす）。

```bash
cd ~/使い方動画 && [ -x .venv/bin/python ] || (python3 -m venv .venv && .venv/bin/pip install -q playwright imageio-ffmpeg && .venv/bin/python -m playwright install ffmpeg)
```

- 以後のコマンドは `python3` ではなく `.venv/bin/python` で動かす
- 録画は利用者の Google Chrome を使う。Chrome が無いときだけ `.venv/bin/python -m playwright install chromium` も作業フォルダ用に入れる
- `python3` 自体が無い Mac（まれ）のときだけ、利用者に「Xcode のコマンドラインツールを入れてください（画面の案内で「インストール」を押すだけ）」と1行で伝える

## 進め方

1. **聞く（短く）**：どのページか（URL）／誰に何を伝える動画か／長さ（目安 1〜2分）／ログインが要るページか
   - ログインが要るページは、ログイン不要の公開ページで作るか、利用者に相談する。パスワードを台本に書かない
2. **ページを見る**：実際に開いて、押すボタン・見せたい場所の見分け方（`#id`・`text=ボタンの文字`・CSSセレクタ）を調べる
3. **台本を書く**：`guides/<名前>.json`。書き方は `scripts/record_guide.py` の先頭と `guides/sample.json`
4. **録画**：`.venv/bin/python scripts/record_guide.py guides/<名前>.json` → `out/<名前>.mp4`
5. **確かめる**：数秒おきのコマを1枚に並べて見る。字幕が画面の大事な所に重なっていないか、押した結果が画面に出ているか、字幕と画面の内容が合っているか
   ```bash
   .venv/bin/python -c "import imageio_ffmpeg,subprocess,sys;subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i','out/<名前>.mp4','-vf','fps=1/4,scale=640:-1,tile=3x3','-frames:v','1','out/<名前>_check.png'])"
   ```
6. **渡す**：mp4 の場所と長さを伝える。直したい所を聞いて、台本を直して録り直す

## 台本の決まり（ここで見やすさが決まる）

- **1手順＝1つのこと**。字幕は1行〜2行（40字以内）
- 最初の字幕で「何の使い方か」を言う
- 押す前に字幕で「次に何をするか」を言う（例：「UI / UX の棚を開いてみます」）
- 画面に無いこと・実際に起きないことを字幕に書かない。録画を見て確かめる
- 押す所は `click`（青い丸）、見せたいだけの所は `point`（オレンジの枠）
- 字幕を読む時間は自動（1秒に約7文字）。足りなければ `sec` で延ばす
- 最後は字幕を消して1秒止めて終わる（`{"caption": "", "do": "wait", "sec": 1}`）

## うまくいかないとき

- 「見つかりません」「Timeout」：`target` が違う。ページを開いて、そのボタンの id や文字を確かめる。同じ文字が複数あるときは `.親のクラス >> text=文字` で絞る
- 画面が真っ白で始まる：ページの読み込みが遅い。最初に `{"do": "wait", "sec": 2}` を足す
- 動画が長すぎる：手順を減らすか、`sec` を短くする
