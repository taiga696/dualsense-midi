# DualSense MIDI（日本語版）

PS5 の DualSense コントローラーを **MIDI コントローラー化**して、djay Pro などの
DJ / DAW アプリから使えるようにする macOS 向けの軽量ブリッジです。

[English version](README.md)

DualSense は HID ゲームパッドであり MIDI を出力しません。そのため、
間に変換レイヤーを1枚挟むことで「普通の MIDI 機器」として見せます。

```
DualSense --(Bluetooth / USB)--> dualsense_midi.py --(Core MIDI)--> 仮想ポート "DualSense MIDI" --> アプリ
```

Core MIDI の仮想ポートはプロセス内で作られるため、**IAC Driver の設定は不要**です
（スクリプトを終了するとポートも消えます）。

## 必要なもの

- macOS 11 以降（Apple Silicon / Intel 両対応）
- DualSense（Bluetooth でも USB でも可）
- Python 3.9 以上
- MIDI 入力に対応したアプリ（djay Pro など）

> **注意**: djay Pro で MIDI マッピングを使うには **PRO サブスクリプション**が必要です
> （Algoriddim 公式: https://help.algoriddim.com/user-manual/djay-pro-mac/midi/mapping）

## インストール

```bash
git clone https://github.com/taiga696/dualsense-midi.git ~/DualSenseMIDI
cd ~/DualSenseMIDI

python3 -m venv ~/.dualsense-midi-venv
source ~/.dualsense-midi-venv/bin/activate
pip install -r requirements.txt
```

## 使い方

```bash
python3 dualsense_midi.py          # 起動
python3 dualsense_midi.py --probe  # ボタン番号の調査
python3 dualsense_midi.py --ports  # MIDI ポート一覧
python3 dualsense_midi.py --test   # テスト信号を送信
python3 dualsense_midi.py --quiet  # ログを出さない
```

成功するとこう表示されます。

```
[OK] Virtual MIDI port created: DualSense MIDI
[OK] Connected: DualSense Wireless Controller (axes=6, buttons=17)
```

アプリ側の MIDI 入力リストから **「DualSense MIDI」** を選んでください。

### 起動順に注意

djay を含む多くのアプリは**起動時に一度だけ** MIDI 機器を走査します。

1. **先に**このブリッジを起動する
2. そのあとアプリを起動する

すでにアプリが動いている場合は再起動してください（`dj.command` が自動で面倒を見ます）。

### 便利コマンド（macOS）

| コマンド | 内容 |
|---|---|
| `dj.command` | ブリッジ起動 + コントローラ接続チェック + djay Pro 起動/再起動 |
| `start.command` | ブリッジだけ起動 |
| `stop.command` | ブリッジ停止 |
| `button_probe.command` | ボタン番号の調査 |
| `install_service.command` | LaunchAgent として登録（ログイン時自動起動・クラッシュ時自動復帰） |
| `uninstall_service.command` | LaunchAgent の解除 |
| `status.command` | 状態チェック（ブリッジ・LaunchAgent・MIDIポート・Bluetooth・再起動回数） |

```bash
alias dj="$HOME/DualSenseMIDI/dj.command"
```

### おまけ：ログイン時に自動起動する

```bash
cd ~/DualSenseMIDI
./install_service.command
```

LaunchAgent（`~/Library/LaunchAgents/com.dualsense.midi.plist`）として登録され、
`RunAtLoad` + `KeepAlive` により**ログイン時に自動起動・クラッシュ時も自動復帰**します。
「djay より先にブリッジ」という起動順の問題が根本から消えます。ログは `bridge.log` へ。
解除は `./uninstall_service.command`。

※ 通常の Terminal ウィンドウから実行してください（`launchctl` は GUI セッションが必要です）。
GUI で設定したい場合は「システム設定 → 一般 → ログイン項目」に `start.command` を追加してください。

## マッピング

`mapping.json` を書き換えて再起動すると反映されます。

### ボタン → Note

| ボタン | Note | | ボタン | Note |
|---|---|---|---|---|
| □ | 38 | | Create | 48 |
| ✕ | 36 | | Options | 49 |
| ○ | 37 | | L3 | 50 |
| △ | 39 | | R3 | 51 |
| L1 | 44 | | PS | 52 |
| R1 | 45 | | マイクミュート | 53 |
| L2（デジタル） | 46 | | タッチパッド | 54 |
| R2（デジタル） | 47 | | | |

### スティック / トリガー → CC

| 入力 | CC | | 入力 | CC |
|---|---|---|---|---|
| 左スティック X / Y | 7 / 8 | | L2 トリガー | 1 |
| 右スティック X / Y | 10 / 11 | | R2 トリガー | 2 |

> ボタン番号の並びは OS / SDL のバージョンで変わる場合があります。
> 思い通りに動かない時は `--probe` で実番号を確認してください。

> ⚠️ **PSボタンには注意**。軽く押す分には問題ありませんが、**1秒ほど長押しするとコントローラの電源が落ちます**（またはペアリングモードに移行）。Bluetooth が切れて MIDI ポートも消えるため、アプリ側は再起動が必要になります。予備のボタンが欲しい場合は PS ではなく **R1（Note 45）** を使ってください。

## つまずきポイント

| 症状 | 原因 | 対処 |
|---|---|---|
| 「DualSense MIDI」が出てこない | ブリッジ未起動 / アプリより後に起動した | ブリッジ → アプリの順で起動 |
| マッピング画面が開けない（djay） | PRO サブスク未契約 | サブスクが必要 |
| ボタンが反応しない | ボタン番号のズレ | `--probe` で確認して `mapping.json` を修正 |
| コントローラを検出しない | ペアリング切れ | PS + Create 長押しで再ペアリング |

Bluetooth でも遅延は体感ほぼありません（ポーリング 5ms / 200Hz、MIDI は Mac 内部の
Core MIDI を通るため外部バッファがありません）。さらに詰めたい場合は USB 接続にしてください。

## 仕組み

- 入力: `pygame`（SDL 2.x）でゲームパッドを読む
- 出力: `python-rtmidi` の仮想ポート（Core MIDI の `MIDIDestinationCreate`）
- ポーリング: 5ms ごとに状態を直接読み、イベント頼みにしない（取りこぼし防止）
- IAC Driver の設定も、サードパーティアプリもカーネル拡張も不要

## 限界

- **macOS 専用**（Windows は `GameControllers2MIDI` + `loopMIDI` で同じ考え方が使えますが未検証）
- **ジョグホイールがない**のでスクラッチの手応えは出ません
- 2デッキの最小構成が精一杯
- iOS / iPadOS では動きません

## ライセンス

MIT（[LICENSE](LICENSE)）
