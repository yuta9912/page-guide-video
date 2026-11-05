# Webページの使い方動画レシピ（page-guide-video）

Webページを**自動で操作して録画**し、字幕付きの「使い方動画」にするレシピです。
カーソルが動き、押す所に青い丸、見てほしい所にオレンジの枠、画面の下に字幕が出ます。撮影も動画編集ソフトも要りません。費用はかかりません。

## いちばん簡単な始め方

Claude Code を開いて、次の文をそのまま貼るだけです。

> https://github.com/yuta9912/page-guide-video のスキルを ~/.claude/skills/page-guide-video に入れて、準備まで案内して。終わったら、このページの使い方動画を作って：（動画にしたいページのURL）

あとは Claude Code が、道具の準備・台本・録画・確認まで進めてくれます。

## 要るもの

- Mac
- Claude Code
- Google Chrome
- Python 3（Mac に入っていなければ Claude Code が案内します）

## 自分で動かす場合

```bash
python3 -m pip install playwright imageio-ffmpeg
python3 -m playwright install ffmpeg
python3 scripts/record_guide.py guides/sample.json
```

`out/sample.mp4` ができます（DesignNOW のモーションカタログを案内する、約30秒の見本）。
台本の書き方は `guides/sample.json` と `scripts/record_guide.py` の先頭にあります。

## 守ること

- 録画するのは、自分のサイトか、録画して見せてよいページだけにする
- ログインが要るページを録るときは、パスワードや個人情報が画面に映らないようにする
