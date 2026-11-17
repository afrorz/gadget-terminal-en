# Gadget Terminal 英語版(en.gadgetterminal.com)

中国だけで出た新しいガジェットを英語で紹介し、「中国の外で手に入るか」に答えるサイト。
日本語版 GT(`media\GadgetTerminal`)とはリポジトリも仕組みも別(2026-11-17 本人と決定。英語版の試しが日本語版の検索評価と毎朝の公開に響かないようにするため)。

- リポジトリ: `afrorz/gadget-terminal-en`(公開)。main に push すると `deploy.yml` が GitHub Pages に出す
- 組み立て: `python scripts/build.py`(`--serve` で http://localhost:8001)。記事は `content/posts/*.md`
- **日本語版のフォルダとファイルは変更しない。** 記事の材料として読むだけ

## 記事の決まり

- 軸は記事末の `## Can you get it outside China?`。ここで、買える場所(公式の海外店・輸入店・購入代行)、海外版の発表、FCC/CE、中国の外で使えない機能(アプリ・クラウド・言語)、自分の国で買える代わり、を書く
- 数字は公式ページと出典の記事にあるものだけ。分からないことは「We could not confirm」と書く
- 価格・在庫には「at time of writing」を付ける。元(人民元)をドルに換算しない
- 画像は GT と同じ扱い: メーカー公式ページの画像を `thumbnail` にホットリンクし、`thumbnail_credit` に出典。公式写真が無いときだけ、その製品の YouTube 動画を `video`(動画ID)+ `video_credit` で付ける(探し方は `docs/daily-prompt.md`)
- front matter: `title` `slug` `date` `category`(phones/pc/gaming/audio/home/weird) `summary` `availability`(china-only/import/global) `sources`
- 英文は短い文で。煽らない、感嘆符を使わない

## 毎朝の自動の記事づくり(2026-11-18〜)

- `.github/workflows/daily-article.yml` が毎日 06:30 JST 指定(実際は遅れる)で3本書く。手順と決まりは `docs/daily-prompt.md`(**記事の書き方を変えるときはここを直す**)
- 流れ: `scripts/candidates.py` が日本語版のダイジェスト(公開リポジトリから読むだけ)から中国がらみの候補を `data/candidates.md` に出す → Claude が書く → `scripts/check_posts.py` に通らない記事は外す → push → `deploy.yml` が公開
- Claude の利用枠を使う。鍵はリポジトリの secret `CLAUDE_CODE_OAUTH_TOKEN`
- 手動で1本書かせる: Actions の「Daily articles」を Run workflow で URL を入れて回す
