# DualSense MIDI

PS5 の DualSense コントローラーを **MIDI コントローラー化**して、djay Pro などの
DJ / DAW アプリから使えるようにする macOS 向けの軽量ブリッジです。

DualSense は HID ゲームパッドであり MIDI を出力しないため、
間に変換レイヤーを1枚挟むことで「普通の MIDI 機器」として見せます。

```
DualSense --(Bluetooth / USB)--> dualsense_midi.py --(Core MIDI)--> 仮想ポート "DualSense MIDI" --> アプリ
```

## 必要なもの

- macOS 11 以降（Apple Silicon / Intel 両対応）
- DualSense（Bluetooth でも USB でも可）
- Python 3.9 以上
- MIDI 入力に対応したアプリ（djay Pro など）

> **注意**: djay Pro で MIDI マッピングを使うには **PRO サブスクリプション**が必要です
> （Algoriddim 公式: https://help.algoriddim.com/user-manual/djay-pro-mac/midi/mapping）

## インストール

```bash
git clone https://github.com/<あなたのID>/dualsense-midi.git ~/DualSenseMIDI
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
python3 dualsense_midi.py --test   # 動作確認用のテスト信号
```

起動すると仮想 MIDI ポート **「DualSense MIDI」** が作成されます。
アプリ側の MIDI 入力リストから選択してください。

### 便利コマンド（macOS）

| コマンド | 内容 |
|---|---|
| `dj.command` | ブリッジ起動 + コントローラ接続チェック + djay Pro 起動/再起動 |
| `start.command` | ブリッジだけ起動 |
| `stop.command` | ブリッジ停止 |
| `button_probe.command` | ボタン番号の調査 |

`~/.zshrc` に alias を入れると便利です:

```bash
alias dj="$HOME/DualSenseMIDI/dj.command"
```

## マッピング

`mapping.json` を書き換えて再起動すると反映されます。

### ボタン → Note

| ボタン | Note | | ボタン | Note |
|---|---|---|---|---|
| □ | 38 | | L1 | 44 |
| ✕ | 36 | | R1 | 45 |
| ○ | 37 | | L3 | 50 |
| △ | 39 | | R3 | 51 |

### スティック / トリガー → CC

| 入力 | CC | | 入力 | CC |
|---|---|---|---|---|
| 左スティック X / Y | 7 / 8 | | L2 トリガー | 1 |
| 右スティック X / Y | 10 / 11 | | R2 トリガー | 2 |

> ボタン番号の並び順は OS / SDL のバージョンで変わる場合があります。
> 思った通りに動かない時は `--probe` で実際の番号を確認してください。

## 仕組み

- 入力の読み取り: `pygame`（SDL 2.x）
- MIDI 出力: `python-rtmidi` の仮想ポート（Core MIDI の `MIDIDestinationCreate`）
- IAC Driver の設定は不要です
- ポーリング周期 5ms（200Hz）

## ライセンス

MIT
