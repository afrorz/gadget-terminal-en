# Gadget Terminal 英語版(en.gadgetterminal.com)

1つの国・地域だけで出た新しいガジェットを英語で紹介し、「その国の外で手に入るか」に答えるサイト。
対象は中国・日本・韓国・それ以外のアジア・ヨーロッパ(2026-11-18 本人の指示で中国だけから広げた)。
日本語版 GT(`media\GadgetTerminal`)とはリポジトリも仕組みも別(2026-11-17 本人と決定。英語版の試しが日本語版の検索評価と毎朝の公開に響かないようにするため)。

- リポジトリ: `afrorz/gadget-terminal-en`(公開)。main に push すると `deploy.yml` が GitHub Pages に出す
- 組み立て: `python scripts/build.py`(`--serve` で http://localhost:8001)。記事は `content/posts/*.md`
- **日本語版のフォルダとファイルは変更しない。** 記事の材料として読むだけ

## 記事の決まり

- 軸は記事末の `## Can you get it outside <国名>?`(国名は `scripts/regions.py` の名前。点検で突き合わせる)。ここで、買える場所(公式の海外店・輸入店・購入代行)、海外版の発表、FCC/CE、発売国の外で使えない機能(アプリ・クラウド・言語・電圧とプラグ)、自分の国で買える代わり、を書く
- 数字は公式ページと出典の記事にあるものだけ。分からないことは「We could not confirm」と書く
- 価格・在庫には「at time of writing」を付ける。現地の通貨(元・円・ウォン・ユーロなど)をドルに換算しない
- 画像は GT と同じ扱い: メーカー公式ページの画像を `thumbnail` にホットリンクし、`thumbnail_credit` に出典。公式写真が無いときだけ、その製品の YouTube 動画を `video`(動画ID)+ `video_credit` で付ける(探し方は `docs/daily-prompt.md`)。**写真も動画も無い記事は公開しない**(`check_posts.py` で落ちる。2026-11-18 本人の指示。外した記事は `content/drafts/` に置く。ここは組み立てに入らない)
- front matter: `title` `slug` `date` `category`(phones/pc/gaming/audio/home/weird) `summary` `origin`(発売国のコード。cn/jp/kr/in/eu/de など、`scripts/regions.py`) `availability`(home-only/import/global) `sources`。任意で `product`(案内板の短い製品名)・`from`(本社の都市。例 "SZX Shenzhen")
- 見た目は日本語版 GT と同じ(空港の出発案内板)。日本語版から写したスタイルは `design/gt-base.css`、英語版だけの追加は `scripts/build.py` の `EN_CSS`
- 英文は短い文で。煽らない、感嘆符を使わない

## 毎朝の自動の記事づくり(2026-11-18〜)

- `.github/workflows/daily-article.yml` が毎日 06:30 JST 指定(実際は遅れる)で3本書く。手順と決まりは `docs/daily-prompt.md`(**記事の書き方を変えるときはここを直す**)
- 流れ: `scripts/candidates.py` が日本語版のダイジェスト(公開リポジトリから読むだけ)の中国がらみの物と、日本・韓国・インド・ヨーロッパのニュースの RSS(`REGION_FEEDS`)から候補を `data/candidates.md` に国ごとに出す → Claude が書く → `scripts/check_posts.py` に通らない記事は外す → push → `deploy.yml` が公開
- Claude の利用枠を使う。鍵はリポジトリの secret `CLAUDE_CODE_OAUTH_TOKEN`
- 手動で1本書かせる: Actions の「Daily articles」を Run workflow で URL を入れて回す
