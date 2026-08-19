# GodiNavi v1.3.0

## 日本語

### バフ認識の改善

- 一部の環境で「炎の結晶」バフが正常に認識されない問題を修正しました。

### パーティールーム機能の強化

- パーティールームの有効期限を廃止しました。
- 全員がパーティールームから退出すると、そのルームは削除されます。
- 全員が未接続の状態で10日が経過すると、そのルームは自動的に削除されます。

#### プロフィール管理

- 複数のキャラクターの名前・職業・副職業をプロフィールとして保存できる機能を追加しました。
- パーティールームの作成・入室時に、保存したプロフィールを選択できます。
- 入室後も「パーティールーム確認」画面で自分のカードをクリックし、プロフィールの変更や管理を行えます。
- パーティーリーダーは自分のカードをクリックすることで、過去に追放したユーザーの一覧やメモを管理し、追放を解除できます。

#### チャット・システム通知

- パーティールームにチャット機能を追加しました。
- メンバーの入室・退出・接続状態の変更などがシステムメッセージとして表示されます。
- 「パーティールーム確認」画面の「チャット」ボタンから、チャット履歴や各種設定を管理できます。
- チャット効果音は初期設定ではOFFになっています。ONにすると音量を調整できます。
- チャットオーバーレイを有効にすると、パーティールーム確認画面を閉じた状態でもチャットやシステム通知を確認し、メッセージを送信できます。

#### チャット通報

- 通報したいチャットメッセージを右クリックすると、通報メニューが表示されます。
- 通報すると、選択したメッセージを含む直前の会話が最大20件までサーバーへ送信されます。
- この機能はユーザー間のトラブルを仲裁するためのものではなく、違法行為が疑われる会話について関連資料を提出するための機能です。単なるユーザー間のトラブルには使用をお控えください。
- チャットを初めて利用する際に、チャット機能および通報データの取り扱いに関する案内・同意画面が表示されます。
- チャットの利用に同意しない場合でも、メンバーの入室・退出・接続状態などのシステム通知は引き続き確認できます。

### パーティールームサーバーの状態表示

- ツールバーのパーティールームアイコンにマウスカーソルを合わせると表示されるメニューから、パーティールームサーバーの稼働状態を確認できます。
- サーバーを利用できない場合、パーティールームの作成・入室機能は無効になります。

---

## 한국어

### 버프 인식 개선

- 일부 이용 환경에서 `불의 결정` 버프가 정상적으로 인식되지 않던 문제를 해결하였습니다.

### 파티룸 기능 강화

- 파티룸의 유효기간 제한을 제거하였습니다.
- 파티룸에서 모든 인원이 퇴실하면 해당 방이 삭제됩니다.
- 모든 인원이 연결되지 않은 상태로 10일이 지나면 해당 방이 자동으로 삭제됩니다.

#### 프로필 관리

- 여러 캐릭터의 닉네임, 직업 및 부직업 정보를 프로필로 저장할 수 있는 기능을 추가하였습니다.
- 파티룸을 개설하거나 입실할 때 저장된 프로필을 선택할 수 있습니다.
- 파티룸 입실 후에도 `파티룸 확인` 창에서 자신의 카드를 클릭하여 프로필을 변경하거나 관리할 수 있습니다.
- 파티장은 자신의 카드를 클릭하여 기존에 추방한 이용자 목록과 메모를 관리하고, 추방을 해제할 수 있습니다.

#### 채팅 및 시스템 알림

- 파티룸 채팅 기능을 추가하였습니다.
- 파티원의 입실, 퇴실 및 연결 상태 변경 등의 알림이 시스템 메시지로 표시됩니다.
- `파티룸 확인` 창의 `채팅` 버튼을 통해 채팅 내역과 관련 설정을 관리할 수 있습니다.
- 채팅 효과음은 기본적으로 꺼져 있으며, 활성화하면 음량을 조절할 수 있습니다.
- 채팅 오버레이를 활성화하면 파티룸 확인창을 닫은 상태에서도 채팅과 시스템 알림을 확인하고 메시지를 보낼 수 있습니다.

#### 채팅 신고

- 신고할 채팅 메시지를 마우스 오른쪽 버튼으로 클릭하면 신고 메뉴가 표시됩니다.
- 신고 시 해당 메시지를 포함한 직전 대화가 최대 20건까지 서버로 전송됩니다.
- 이 기능은 이용자 간의 다툼을 중재하기 위한 기능이 아니라, 불법행위가 의심되는 대화의 관련 자료를 제출하기 위한 기능입니다. 단순한 이용자 간 분쟁에는 사용을 자제해 주세요.
- 채팅을 처음 이용할 때 기능과 신고 자료 처리에 관한 안내 및 동의창이 표시됩니다.
- 채팅 이용에 동의하지 않더라도 파티원의 입실·퇴실 및 연결 상태 등의 시스템 알림은 계속 확인할 수 있습니다.

### 파티룸 서버 상태 표시

- 툴바의 파티룸 아이콘에 마우스를 올리면 표시되는 메뉴에서 파티룸 서버의 현재 가동 상태를 확인할 수 있습니다.
- 서버를 이용할 수 없는 상태에서는 파티룸 개설 및 입실 기능이 비활성화됩니다.

---

## English

### Improved Buff Detection

- Fixed an issue where the `Fire Crystal` buff was not detected correctly in certain environments.

### Major Party Room Improvements

- Party Rooms no longer have a fixed expiration time.
- A Party Room is deleted when every member leaves.
- A Party Room is automatically deleted if all members remain disconnected for 10 days.

#### Profile Management

- Added profile management for saving the name, main job, and secondary job of multiple characters.
- Saved profiles can be selected when creating or joining a Party Room.
- After joining, you can click your own card in the `Party Room Overview` window to change or manage your profile.
- Party leaders can click their own card to manage previously banned users, edit the associated notes, or revoke a ban.

#### Chat and System Notifications

- Added a Party Room chat feature.
- Member joins, departures, and connection-status changes are displayed as system messages.
- Chat history and related options can be managed through the `Chat` button in the `Party Room Overview` window.
- Chat sound effects are disabled by default. When enabled, their volume can be adjusted.
- When the chat overlay is enabled, you can read chat messages and system notifications—and send messages—even while the Party Room Overview window is closed.

#### Chat Reports

- Right-click the chat message you want to report to open the report menu.
- A report submits up to 20 recent messages ending with the selected message to the server.
- This feature is intended to submit relevant records of conversations involving suspected illegal activity. It is not intended to mediate arguments or disputes between users, so please refrain from using it for ordinary personal disputes.
- An information and consent notice about the chat feature and report-data handling is displayed when you use chat for the first time.
- Even if you decline the chat feature, you can still receive system notifications about member joins, departures, and connection-status changes.

### Party Room Server Status

- Hover over the Party Room icon on the toolbar to view the current operating status of the Party Room server.
- Party Room creation and joining are disabled while the server is unavailable.
