# GodiNavi / ガディナビ / 가디내비

> ### [⬇ GodiNavi 2.0.0 Download](https://github.com/GD-fandev/godinavi/releases/tag/v2.0.0)

## 目次 / 목차 / Table of Contents

- [日本語](#日本語)
  - [GodiNaviとは](#godinaviとは)
  - [主な機能](#主な機能)
  - [はじめに](#はじめに)
  - [解説動画](#解説動画)
  - [冒険者様を募集しています](#冒険者様を募集しています)
  - [調査にご協力してくださった冒険者様](#調査にご協力してくださった冒険者様special-thanks)
  - [設定・トラブルシューティング](#設定トラブルシューティング)
  - [ライセンスと注意事項](#ライセンスと注意事項)
- [한국어](#한국어)
  - [가디내비 소개](#가디내비-소개)
  - [주요 기능](#주요-기능-1)
  - [시작하기](#시작하기)
  - [해설 영상](#해설-영상)
  - [설정 및 문제 해결](#설정-및-문제-해결)
  - [라이선스 및 주의사항](#라이선스-및-주의사항)
- [English](#english)
  - [About GodiNavi](#about-godinavi)
  - [Features](#features)
  - [Getting Started](#getting-started)
  - [Configuration and Troubleshooting](#configuration-and-troubleshooting)
  - [License and Notices](#license-and-notices)

---

## 日本語

### GodiNaviとは

GodiNavi（ガディナビ）は、ガディウスのプレイに必要な便利機能を一つにまとめたゲーム内オーバーレイツールです。

### 主な機能

- ミニマップとワールドマップ
- ポータルコマンドの登録・コピーとプリセット管理
- バフタイマー
- 武器・鎧・盾の耐久度監視と警告
- 日本語・韓国語・英語UI
- マップデータおよびGodiNavi本体のアップデート

### はじめに

1. 初回起動時に、画面の案内に従ってバフ認識領域とマップOCR領域を設定してください。
2. 歯車アイコンを左クリックすると、メインボタンの位置やサイズを調整できます。
3. 各ボタンにマウスカーソルを合わせると、その機能のメニューが表示されます。実際に操作しながら必要な機能を確認してください。
4. 旧GodiMapで使用していた `F11` 操作は廃止されました。現在の専用ショートカットは、ワールドマップを開閉する `F10` のみです。それ以外の操作はオーバーレイボタンから行います。

### 解説動画

- [日本語版 解説動画](https://youtu.be/fcWgLNT3ayk)

### 冒険者様を募集しています

ガディナビには、まだ測量が完了していない未調査地域があります。

現在の未調査地域は以下の通りです。

- カールマーニュ洞窟 1F
- 中部背骨洞窟 1F
- 西部背骨洞窟 4～5F
- シャドミュム洞窟 5～6F
- エブリン・エチリン洞窟 2～5F
- ヘル 1～10F

これらの地域は入場条件のため制作者自身での調査が難しく、現時点では多くの地図が未完成となっています。十分な状態でお届けできず申し訳ありませんが、いつか自分で調査するか、有志の方のお力を借りながら、少しずつ完成させていきたいと考えています。

未知の地へ赴き、地図の完成に力を貸してくださる勇気ある冒険者様を募集しています。ご協力いただける方は、Discordにて制作者までDMをお送りいただけますと幸いです。

ささやかですが感謝の印として、次回の配布時に地図の完成へご協力くださった冒険者様のお名前を、該当地域のミニマップ左下に刻ませていただきたいと思います。

皆様の冒険の記録が、次にその地を訪れる冒険者様の道標となります。ご協力を心よりお待ちしております。

### 調査にご協力してくださった冒険者様（Special Thanks）

- レゲ地下洞窟 9～10F：狐 様
- シャドミュム洞窟 3～4F：狐 様
- エブリン・エチリン洞窟 1F：狐 様

### 設定・トラブルシューティング

個人設定は次の場所へ保存されます。

```text
%LOCALAPPDATA%\GodiNavi\godinavi-config.json
```

表示言語、OCR範囲、ウィンドウ位置、ミニマップとワールドマップの設定、お気に入り情報などが保存されます。完全に初期化する場合は、ガディナビ終了後にこのファイルをバックアップしてから移動または削除してください。

#### Godius Clientが見つからない

- ゲームが起動中か、最小化されていないか確認してください。
- ゲームを管理者権限で起動している場合、ガディナビにも同等の権限が必要になることがあります。

#### キーボードで移動できない

Godiusとガディナビの互換モードおよび管理者権限の設定が異なる場合、キーボードによる移動ができない、動作が重くなる、フリーズするといった問題が発生することがあります。両方の互換性設定を同じ状態にしてください。

基本的には、管理者権限は両方とも無効にすることを推奨します。GodiusをWindows 8互換モードで実行している場合は、ガディナビにも同じ互換モードを設定してください。

それでも移動キーが反応しない場合は、キャプチャー範囲編集モードを終了してから、左Shift、右Shift、左Ctrl、右Ctrlをそれぞれ一度ずつ押して離すと改善する場合があります。

#### OCRが認識しない、または途切れる

- 地域名・座標範囲を再設定し、文字切れや余分なUIがないか確認してください。
- 解像度やゲームUI配置を変更した場合は再設定してください。
- マウスオーバー等による短い欠落では、最後の正常なマップを一定時間維持します。

#### ミニマップが表示されない

- 状態欄とOCR結果を確認してください。
- `maps`と`mapdata`に該当地域が含まれているか確認してください。
- ZIPから配布物全体を展開したか確認してください。

### ライセンスと注意事項

- ガディナビ独自のソースコードは[MIT License](https://github.com/GD-fandev/godinavi/blob/main/LICENSE.txt)で公開しています。
- ゲーム関連素材、地図画像、アイコン等はMIT Licenseの対象外です。詳細は[Asset Notice](https://github.com/GD-fandev/godinavi/blob/main/licenses/ASSET_NOTICE.txt)をご確認ください。
- ダンジョン地図画像の出典：[Godius公式ホームページ](https://www.godius.co.kr/guide_8?t_id=2)
- 町の地図画像の出典：[Godius Online Forum](http://godius.s201.xrea.com/mmain.html)
- フィールド地図画像の出典：[フィールドマップ](https://www3.hp-ez.com/hp/chombo/field)
- モンスター名の日本語表記情報：[Godius＠モブ表・レアドロ実績表](https://docs.google.com/spreadsheets/d/1HVeLbYElGRoVfSbh26oiRwD-ZGLhCBVE3GfKPZ55Jvc/edit?gid=1783106804#gid=1783106804&fvid=445972214)
- 第三者ソフトウェアとOCRモデルについては[Third-Party Notices](https://github.com/GD-fandev/godinavi/blob/main/licenses/THIRD_PARTY_NOTICES.txt)と`licenses/third_party`をご確認ください。
- ガディナビは非公式ツールです。ゲーム運営方針および素材提供元の規約に従い、各自の判断でご利用ください。

---

## 한국어

### 가디내비 소개

가디내비는 가디우스 플레이에 필요한 편의 기능을 하나로 모은 인게임 오버레이 도구입니다.

### 주요 기능

- 미니맵과 월드맵
- 포탈 명령어 등록·복사 및 프리셋 관리
- 버프 타이머
- 무기·갑옷·방패 내구도 감시 및 경고
- 한국어·日本語·English UI
- 지도 데이터 및 가디내비 본체 업데이트

### 시작하기

1. 처음 실행하면 화면에 표시되는 안내에 따라 버프 인식 영역과 지도 OCR 영역을 지정하세요.
2. 톱니바퀴 아이콘을 좌클릭하면 메인 버튼의 위치와 크기를 조절할 수 있습니다.
3. 각 버튼에 마우스를 올리면 해당 기능의 메뉴가 나타납니다. 직접 눌러보며 필요한 기능과 사용법을 확인하세요.
4. 기존 가디맵에서 사용하던 `F11` 조작은 없어졌습니다. 현재 별도의 단축키는 월드맵을 열고 닫는 `F10`뿐이며, 나머지 기능은 오버레이 버튼으로 조작합니다.

### 해설 영상

- [한국어판 해설영상](https://youtu.be/eCkEvMEkAuc)

### 설정 및 문제 해결

개인 설정은 다음 위치에 저장됩니다.

```text
%LOCALAPPDATA%\GodiNavi\godinavi-config.json
```

표시 언어, OCR 영역, 창 위치, 미니맵과 월드맵 설정, 즐겨찾기 정보 등이 저장됩니다. 완전히 초기화하려면 가디내비를 종료한 뒤 이 파일을 백업하고 이동하거나 삭제하세요.

#### Godius Client를 찾을 수 없는 경우

- 게임이 실행 중인지, 최소화되어 있지는 않은지 확인하세요.
- 게임을 관리자 권한으로 실행했다면 가디내비에도 같은 권한이 필요할 수 있습니다.

#### 키보드로 이동할 수 없는 경우

Godius와 가디내비의 호환 모드 또는 관리자 권한 설정이 서로 다르면 키보드 이동이 되지 않거나, 동작이 느려지거나, 프로그램이 멈추는 문제가 발생할 수 있습니다. 두 프로그램의 호환성 설정을 동일하게 맞추세요.

기본적으로 두 프로그램 모두 관리자 권한을 사용하지 않는 것을 권장합니다. Godius를 Windows 8 호환 모드로 실행한다면 가디내비에도 같은 호환 모드를 설정하세요.

그래도 이동 키가 반응하지 않으면 캡처 영역 편집 모드를 종료한 뒤 왼쪽 Shift, 오른쪽 Shift, 왼쪽 Ctrl, 오른쪽 Ctrl 키를 각각 한 번씩 눌렀다가 떼어 보세요.

#### OCR이 인식되지 않거나 끊기는 경우

- 지역명·좌표 영역을 다시 설정하고, 글자가 잘리거나 불필요한 UI가 포함되지 않았는지 확인하세요.
- 해상도나 게임 UI 배치를 변경했다면 영역을 다시 설정하세요.
- 마우스 오버 등으로 잠시 인식이 끊기면 마지막으로 정상 인식된 지도를 일정 시간 유지합니다.

#### 미니맵이 표시되지 않는 경우

- 상태 표시와 OCR 결과를 확인하세요.
- `maps`와 `mapdata`에 해당 지역이 포함되어 있는지 확인하세요.
- ZIP 배포본 전체를 압축 해제했는지 확인하세요.

### 라이선스 및 주의사항

- 가디내비 고유 소스 코드는 [MIT License](https://github.com/GD-fandev/godinavi/blob/main/LICENSE.txt)로 공개됩니다.
- 게임 관련 리소스, 지도 이미지, 아이콘 등은 MIT License 적용 대상이 아닙니다. 자세한 내용은 [Asset Notice](https://github.com/GD-fandev/godinavi/blob/main/licenses/ASSET_NOTICE.txt)를 확인하세요.
- 던전 지도 이미지 출처: [Godius 공식 홈페이지](https://www.godius.co.kr/guide_8?t_id=2)
- 마을 지도 이미지 출처: [Godius Online Forum](http://godius.s201.xrea.com/mmain.html)
- 필드 지도 이미지 출처: [필드맵](https://www3.hp-ez.com/hp/chombo/field)
- 제3자 소프트웨어와 OCR 모델은 [Third-Party Notices](https://github.com/GD-fandev/godinavi/blob/main/licenses/THIRD_PARTY_NOTICES.txt) 및 `licenses/third_party`를 확인하세요.
- 가디내비는 비공식 도구입니다. 게임 운영 정책과 리소스 제공처의 약관을 준수하고 각자의 판단과 책임에 따라 사용하세요.

---

## English

### About GodiNavi

GodiNavi is an in-game overlay that brings together useful tools for playing Godius.

### Features

- Minimap and world map
- Portal command registration, copying, and preset management
- Buff timer
- Weapon, armor, and shield durability monitoring and warnings
- Japanese, Korean, and English UI
- Map data and GodiNavi application updates

### Getting Started

1. On the first launch, follow the on-screen guide to configure the buff detection region and map OCR regions.
2. Left-click the gear icon to adjust the position and size of the main buttons.
3. Hover over each button to open its feature menu. Explore the available controls directly to learn how each feature works.
4. The `F11` control from the previous GodiMap is no longer used. The only dedicated shortcut is `F10`, which opens and closes the world map. All other features are controlled through the overlay buttons.

### Configuration and Troubleshooting

Your personal settings are stored at:

```text
%LOCALAPPDATA%\GodiNavi\godinavi-config.json
```

This file stores settings such as the display language, OCR regions, window positions, minimap and world map preferences, and favorites. To reset GodiNavi completely, close the application, back up this file, and then move or delete it.

#### Godius Client cannot be found

- Make sure the game is running and is not minimized.
- If the game is running as administrator, GodiNavi may need the same privileges.

#### Keyboard movement does not work

If Godius and GodiNavi use different compatibility-mode or administrator settings, keyboard movement may stop working, performance may degrade, or the applications may freeze. Configure both applications with the same compatibility settings.

We generally recommend disabling administrator privileges for both applications. If Godius runs in Windows 8 compatibility mode, configure GodiNavi to use the same mode.

If the movement keys still do not respond, exit capture-region editing mode, then press and release Left Shift, Right Shift, Left Ctrl, and Right Ctrl once each.

#### OCR does not recognize text or recognition is intermittent

- Reconfigure the region-name and coordinate regions, and check for clipped text or unrelated UI elements.
- Reconfigure the regions after changing the resolution or game UI layout.
- For brief recognition gaps caused by mouse hover or similar events, GodiNavi keeps the last successfully recognized map for a short time.

#### The minimap is not displayed

- Check the status display and OCR results.
- Make sure the relevant area is included in `maps` and `mapdata`.
- Make sure you extracted the entire ZIP distribution.

### License and Notices

- GodiNavi's original source code is available under the [MIT License](https://github.com/GD-fandev/godinavi/blob/main/LICENSE.txt).
- Game-related assets, map images, icons, and similar materials are not covered by the MIT License. See the [Asset Notice](https://github.com/GD-fandev/godinavi/blob/main/licenses/ASSET_NOTICE.txt) for details.
- Dungeon map image source: [Official Godius website](https://www.godius.co.kr/guide_8?t_id=2)
- Town map image source: [Godius Online Forum](http://godius.s201.xrea.com/mmain.html)
- Field map image source: [Field Map](https://www3.hp-ez.com/hp/chombo/field)
- For third-party software and OCR models, see the [Third-Party Notices](https://github.com/GD-fandev/godinavi/blob/main/licenses/THIRD_PARTY_NOTICES.txt) and `licenses/third_party`.
- GodiNavi is an unofficial tool. Follow the game operator's policies and the terms of the asset providers, and use it at your own discretion and responsibility.
